import time
import threading
import logging
import pandas as pd
from typing import Optional, List, Dict, Any, Callable
from .provider import IDataProvider, DataDimension, SyncPolicy, DataCategory

class DataAggregator(IDataProvider):
    """
    中间层代理，负责：
    1. 请求合并 (Request Coalescing / SingleFlight): 多个并发的相同请求只执行一次。
    2. 短时缓存 (TTL Cache): 极短时间内重复请求直接返回缓存。
    3. 数据过滤: 对于全量数据接口（如 get_snapshot），统一获取后在内存中过滤，
       避免因请求不同参数（子集）而多次触发底层全量请求。
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
        # 假设 provider 有这个方法（BaseFetcher 有）
        if hasattr(self._provider, 'get_save_path'):
            return self._provider.get_save_path(category, filename)
        return filename

    # --- 核心逻辑 ---

    def _get_or_fetch(self, key: str, fetch_func: Callable, force_refresh: bool = False):
        """
        核心方法：检查缓存 -> (如果缺失) 加锁 -> 再次检查缓存 -> 执行请求 -> 存缓存 -> 返回
        """
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
            # 因为在等待锁的过程中，可能前一个线程已经完成了请求并写入了缓存
            with self._cache_lock:
                if not force_refresh and key in self._cache:
                    data, ts = self._cache[key]
                    if time.time() - ts < self._cache_ttl:
                        self._logger.debug(f"Cache hit for {key} (waited)")
                        return data

            # 真的需要执行请求了
            self._logger.debug(f"Executing real fetch for {key}")
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
                # 可选：清理锁对象以防内存泄漏（如果 key 无限多），但对于有限 key 可以保留
                pass

    # --- 接口实现 ---

    def get_price(self, code: str, date: str) -> Optional[float]:
        # get_price 通常是轻量级或通过 get_snapshot 实现。
        # 如果底层是单独请求，这里可以缓存。
        key = f"price:{code}:{date}"
        return self._get_or_fetch(key, lambda: self._provider.get_price(code, date))

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        # 历史数据通常较大且不常变，可以缓存较长时间，或者根据需求不缓存（太大占内存）。
        # 这里演示做个简单缓存，Key 包含日期范围。
        key = f"hist:{code}:{start_date}:{end_date}"
        # 考虑到历史数据量大，这里是否缓存需要权衡。
        # 暂时开启，假设内存足够。
        return self._get_or_fetch(key, lambda: self._provider.get_history(code, start_date, end_date))

    def get_snapshot(self, codes: List[str]) -> List[dict]:
        """
        这是优化的重点。
        假设底层的 AKShareAdapter 在 get_snapshot 时其实是获取全市场数据然后过滤。
        我们在这里拦截：统一获取“全市场”数据并缓存，然后根据 codes 过滤。
        """
        # 定义一个特殊的 key 表示“全市场快照”
        # 注意：这里假设底层的 snapshot 也是基于全市场的。
        # 如果底层真的支持只查几个代码（如 Sina），那这种全量缓存可能反而低效。
        # 但对于 AKShare (stock_zh_a_spot_em)，它是全量的。
        
        # 为了通用性，我们这里做一个假设：
        # 如果是 AKShare，我们用全量缓存策略。
        # 我们可以通过 provider 的类型判断，或者默认采用“按需缓存”策略。
        
        # 策略 A: 总是获取全量并缓存 (适合 AKShare)
        # 策略 B: 按请求的 codes 生成 key (适合 Sina)
        
        # 策略 A: 总是获取全量并缓存 (适合 AKShare 或任何支持全量获取的 Provider)
        # 如果 Provider 提供了 get_full_snapshot，我们优先使用全量缓存策略，
        # 这样不同模块请求不同子集时，只需请求一次全量数据。
        
        if hasattr(self._provider, 'get_full_snapshot'):
            # 1. 获取（或等待）全量数据
            full_data_key = "snapshot_full_raw"
            full_data = self._get_or_fetch(full_data_key, self._provider.get_full_snapshot)
            
            # 2. 在内存中过滤
            # 假设 full_data 是 DataFrame 或 list of dict
            if isinstance(full_data, pd.DataFrame):
                # 假设 Adapter 返回规范化的 DataFrame (AKShareAdapter 是这样的)
                # 列名映射: 代码, 名称, 最新价, ...
                # 我们需要按照 requested codes 过滤
                
                # 注意：这里我们假设了 DataFrame 的结构，这有一点耦合。
                # 但考虑到这是针对表格型数据的通用优化，尚可接受。
                # AKShareAdapter 返回的 DataFrame 包含 '代码' 列。
                
                clean_codes = [c.split('.')[0] for c in codes]
                
                # 检查是否存在 '代码' 列
                if '代码' in full_data.columns:
                    mask = full_data['代码'].isin(clean_codes)
                    subset = full_data[mask]
                    
                    results = []
                    for _, row in subset.iterrows():
                        try:
                            # 尝试构建结果，尽可能匹配 get_snapshot 的返回格式
                            # 注意：这里需要知道列名映射，这通常是 Adapter 的责任。
                            # Aggregator 不应该知道 '最新价' 对应 'price'。
                            
                            # 改进：如果这是一个 DataFrame，我们很难通用的转成 dict list
                            # 除非我们知道 schema。
                            
                            # 替代方案：让 Adapter 提供一个 helper 叫做 `filter_snapshot(full_data, codes)`
                            # 但为了不增加太多 Adapter 的负担，我们在 AKShareAdapter 里虽然有 filter 逻辑，
                            # 这里重复了一遍。
                            
                            # 既然我们已经修改了 AKShareAdapter 的 get_snapshot 来使用 get_full_snapshot
                            # 并在 Adapter 内部做过滤。
                            # 那么 Aggregator 其实不需要在这里做“过滤逻辑”！
                            
                            # 等等，Aggregator 的职责是 Request Coalescing。
                            # 如果 Adapter.get_snapshot 内部调用 self.get_full_snapshot()
                            # 并且 Aggregator 代理了 get_full_snapshot() 的调用（通过 __getattr__ 或者是显式方法）
                            # 那么 Aggregator 只需要缓存 get_full_snapshot 的结果即可！
                            
                            # 让我们看看现在的结构：
                            # Aggregator 包装了 Provider。
                            # Provider.get_snapshot 调用 self.get_full_snapshot()。
                            # 这里的 `self` 是 Provider 实例本身，而不是 Aggregator 包装器！
                            # 所以 Provider 内部的互相调用 **不会** 经过 Aggregator 的缓存层。
                            
                            # 这是一个经典问题。
                            # 解决方案 1: Aggregator 拦截 get_snapshot，自己调用 Provider.get_full_snapshot (经过缓存)，然后自己过滤。
                            # 解决方案 2: Provider 接受一个 cached_loader。
                            
                            # 当前代码是在 Aggregator 里拦截 get_snapshot。
                            # 所以我们需要在这里做过滤。
                            
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
                    self._logger.warning("get_full_snapshot returned DataFrame without '代码' column")
                    return []
            
            elif isinstance(full_data, list):
                # 假设是 list of dict
                clean_codes = set(c.split('.')[0] for c in codes)
                return [item for item in full_data if item.get('code') in clean_codes]
            
            return [] # Fallback
            
        else:
            # 对于非 AKShare (如 Local, Sina)，或者不支持全量的，直接合并相同请求
            codes_tuple = tuple(sorted(codes))
            key = f"snapshot:{hash(codes_tuple)}"
            return self._get_or_fetch(key, lambda: self._provider.get_snapshot(codes))

    def get_table(self, table_name: str, date: Optional[str] = None) -> pd.DataFrame:
        key = f"table:{table_name}:{date}"
        return self._get_or_fetch(key, lambda: self._provider.get_table(table_name, date))
    
    # 转发其他可能的方法
    def __getattr__(self, name):
        return getattr(self._provider, name)
