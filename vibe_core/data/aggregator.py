import time
import threading
import logging
import pandas as pd
from typing import Optional, List, Dict, Any, Callable
from collections import defaultdict
from .provider import IDataProvider, DataDimension, SyncPolicy, DataCategory

class DataAggregator(IDataProvider):
    """
    中间层代理，负责：
    1. 请求合并 (Request Coalescing / SingleFlight): 多个并发的相同请求只执行一次。
    2. 短时缓存 (TTL Cache): 极短时间内重复请求直接返回缓存。
    3. 数据过滤: 对于全量数据接口（如 get_snapshot），统一获取后在内存中过滤，
       避免因请求不同参数（子集）而多次触发底层全量请求。
    4. 智能日志: 初次调用立即记录，后续每分钟汇总记录。
    """
    def __init__(self, provider: IDataProvider, cache_ttl: int = 5):
        """
        :param provider: 实际的数据适配器
        :param cache_ttl: 缓存有效期（秒），默认 5 秒
        """
        self._provider = provider
        self._cache_ttl = cache_ttl
        self._logger = logging.getLogger("vibe.data.aggregator")
        
        # 缓存存储: { key: (data, timestamp) }
        self._cache: Dict[str, tuple] = {}
        self._cache_lock = threading.RLock()
        
        # 正在进行的请求锁: { key: lock }
        self._flight_locks: Dict[str, threading.Lock] = {}
        self._flight_locks_lock = threading.Lock() # 保护 _flight_locks 字典本身

        # 日志统计
        self._log_stats = defaultdict(int)
        self._first_log_done = set()
        self._last_summary_time = time.time()
        self._log_lock = threading.Lock()

    # --- 代理属性 ---
    @property
    def data_dimension(self) -> DataDimension:
        return self._provider.data_dimension

    @property
    def sync_policy(self) -> SyncPolicy:
        return self._provider.sync_policy

    @property
    def archive_filename_template(self) -> str:
        return self._provider.archive_filename_template

    def get_archive_filename(self, **kwargs) -> str:
        return self._provider.get_archive_filename(**kwargs)
        
    def get_save_path(self, category: DataCategory, filename: str) -> str:
        if hasattr(self._provider, 'get_save_path'):
            return self._provider.get_save_path(category, filename)
        return filename

    # --- 智能日志 ---
    def _smart_log(self, tag: str, msg: str):
        """
        初次立即打印 INFO，后续仅计数，每分钟汇总。
        """
        with self._log_lock:
            now = time.time()
            provider_name = self._provider.__class__.__name__
            full_tag = f"{provider_name}:{tag}"
            
            # 1. 初次日志
            if full_tag not in self._first_log_done:
                self._logger.info(f"[{full_tag}] First Fetch: {msg}")
                self._first_log_done.add(full_tag)
                return

            # 2. 计数
            self._log_stats[full_tag] += 1
            
            # 3. 检查汇总 (60s)
            if now - self._last_summary_time >= 60:
                summary = []
                for k, v in self._log_stats.items():
                    if v > 0:
                        summary.append(f"{k}: {v} calls")
                
                if summary:
                    self._logger.info(f"[Data Activity Summary 60s] {', '.join(summary)}")
                
                # 重置计数和时间
                self._log_stats.clear()
                self._last_summary_time = now

    # --- 核心逻辑 ---

    def _get_or_fetch(self, key: str, fetch_func: Callable, force_refresh: bool = False, log_tag: str = "Unknown"):
        """
        核心方法：检查缓存 -> (如果缺失) 加锁 -> 再次检查缓存 -> 执行请求 -> 存缓存 -> 返回
        """
        # 0. 记录活动
        self._smart_log(log_tag, f"Key={key}")

        # 1. 快速检查缓存 (读)
        with self._cache_lock:
            if not force_refresh and key in self._cache:
                data, ts = self._cache[key]
                if time.time() - ts < self._cache_ttl:
                    return data

        # 2. 获取该 Key 对应的执行锁 (SingleFlight)
        with self._flight_locks_lock:
            if key not in self._flight_locks:
                self._flight_locks[key] = threading.Lock()
            lock = self._flight_locks[key]

        # 3. 执行临界区
        with lock:
            # 双重检查锁 (Double-Checked Locking)
            with self._cache_lock:
                if not force_refresh and key in self._cache:
                    data, ts = self._cache[key]
                    if time.time() - ts < self._cache_ttl:
                        # self._logger.debug(f"Cache hit for {key} (waited)")
                        return data

            # 真的需要执行请求了
            # self._logger.debug(f"Executing real fetch for {key}")
            try:
                result = fetch_func()
                
                # 写入缓存
                with self._cache_lock:
                    self._cache[key] = (result, time.time())
                
                return result
            except Exception as e:
                self._logger.error(f"Error fetching {key}: {e}")
                raise e
            finally:
                pass

    # --- 接口实现 ---

    def get_price(self, code: str, date: str) -> Optional[float]:
        key = f"price:{code}:{date}"
        return self._get_or_fetch(key, lambda: self._provider.get_price(code, date), log_tag="get_price")

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        key = f"hist:{code}:{start_date}:{end_date}"
        return self._get_or_fetch(key, lambda: self._provider.get_history(code, start_date, end_date), log_tag="get_history")

    def get_snapshot(self, codes: List[str]) -> List[dict]:
        # 策略 A: 总是获取全量并缓存 (适合 AKShare 或任何支持全量获取的 Provider)
        if hasattr(self._provider, 'get_full_snapshot'):
            # 记录全量请求
            self._smart_log("get_full_snapshot", "Fetching full market snapshot")
            
            full_data_key = "snapshot_full_raw"
            # 这里直接调用 _get_or_fetch，注意不要 double log，传入 log_tag="" 或特定值
            # 实际上我们希望记录 "full snapshot" 被触发的频率
            full_data = self._get_or_fetch(full_data_key, self._provider.get_full_snapshot, log_tag="get_full_snapshot_internal")
            
            if isinstance(full_data, pd.DataFrame):
                clean_codes = [c.split('.')[0] for c in codes]
                if '代码' in full_data.columns:
                    mask = full_data['代码'].isin(clean_codes)
                    subset = full_data[mask]
                    results = []
                    for _, row in subset.iterrows():
                        try:
                            results.append({
                                "code": row.get('代码'),
                                "name": row.get('名称'),
                                "price": float(row.get('最新价', 0)),
                                "change": float(row.get('涨跌幅', 0)),
                                "open": float(row.get('今开', 0)),
                                "high": float(row.get('最高', 0)),
                                "low": float(row.get('最低', 0)),
                                "vol": float(row.get('成交量', 0))
                            })
                        except ValueError:
                            continue
                    return results
                else:
                    return []
            elif isinstance(full_data, list):
                clean_codes = set(c.split('.')[0] for c in codes)
                return [item for item in full_data if item.get('code') in clean_codes]
            return [] 
        
        else:
            # 对于非 AKShare (如 Local, Sina)，直接合并相同请求
            codes_tuple = tuple(sorted(codes))
            key = f"snapshot:{hash(codes_tuple)}"
            return self._get_or_fetch(key, lambda: self._provider.get_snapshot(codes), log_tag="get_snapshot")

    def get_table(self, table_name: str, date: Optional[str] = None) -> pd.DataFrame:
        key = f"table:{table_name}:{date}"
        return self._get_or_fetch(key, lambda: self._provider.get_table(table_name, date), log_tag=f"get_table_{table_name}")
    
    # 转发其他可能的方法
    def __getattr__(self, name):
        # 对于动态调用的方法，如果不做拦截，就无法记录日志。
        # 但 __getattr__ 返回的是属性/方法。
        # 如果要拦截，需要返回一个 Wrapper。
        attr = getattr(self._provider, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                self._smart_log(f"dynamic_{name}", "Calling dynamic method")
                return attr(*args, **kwargs)
            return wrapper
        return attr