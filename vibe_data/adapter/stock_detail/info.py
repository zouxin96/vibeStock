from ...provider import IDataProvider, DataDimension, SyncPolicy
import logging
import json
import os
import sqlite3
import datetime
import pandas as pd
from typing import Dict, Optional, Any

try:
    import akshare as ak
except ImportError:
    ak = None

class StockInfoAdapter(IDataProvider):
    """
    个股详细信息适配器 (SQLite 版)
    
    特性:
    - 使用 SQLite 存储，支持海量个股信息
    - JSON 字段存储，方便随意扩展字段 (Schema-less)
    - 缓存有效期管理
    """
    
    def __init__(self, db_path="data/storage/stock_info.db"):
        self.logger = logging.getLogger("vibe.data.info")
        self.db_path = db_path
        self.cache_validity_days = 30
        
        # 预加载代码名称映射表
        self._code_name_map = None
        
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                # 创建表: symbol (主键), updated_at (更新日期), data (JSON字符串)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS stock_detail (
                        symbol TEXT PRIMARY KEY,
                        updated_at TEXT,
                        data TEXT
                    )
                ''')
                # 尝试创建索引（如果需要按其他字段查询，这里暂时只用主键）
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to init DB: {e}")

    @property
    def data_dimension(self) -> DataDimension:
        return DataDimension.INFO

    @property
    def sync_policy(self) -> SyncPolicy:
        return SyncPolicy.ON_DEMAND

    @property
    def archive_filename_template(self) -> str:
        return "info.db"

    def _ensure_code_map(self):
        if self._code_name_map is None:
            try:
                # 尝试获取全市场代码表
                # 如果失败，map 将保持为空，依赖后续直接转换
                if ak:
                    df = ak.stock_info_a_code_name()
                    self._code_name_map = dict(zip(df['name'], df['code']))
                    for code in df['code']:
                        self._code_name_map[str(code)] = str(code)
                else:
                    self._code_name_map = {}
            except Exception as e:
                self.logger.warning(f"Failed to load stock code map: {e}. Will rely on direct code usage.")
                self._code_name_map = {}

    def _format_symbol_for_xq(self, code: str) -> str:
        """转换为雪球格式: SH600519, SZ000001, BJ839xxx"""
        code = str(code)
        if code.startswith("SH") or code.startswith("SZ") or code.startswith("BJ"):
            return code
        
        if code.startswith("6"):
            return f"SH{code}"
        elif code.startswith("0") or code.startswith("3"):
            return f"SZ{code}"
        elif code.startswith("4") or code.startswith("8"):
            return f"BJ{code}"
        return f"SH{code}" # Default fallback

    def get_stock_info(self, query: str, only_cache: bool = False) -> Dict[str, Any]:
        """
        获取个股详细信息
        :param query: 股票代码 (600519) 或 名称
        :param only_cache: 如果为 True，仅查询数据库，不存在则返回空字典（不发起网络请求）
        """
        # 1. 规范化 Symbol
        self._ensure_code_map()
        code = self._code_name_map.get(query) or self._code_name_map.get(str(query))
        
        # 如果 query 看起来像代码，直接使用
        if not code and (str(query).isdigit() or str(query).startswith(('SH', 'SZ', 'BJ'))):
            code = query
            
        if not code:
            # self.logger.warning(f"Unknown stock query: {query}")
            return {}

        xq_symbol = self._format_symbol_for_xq(code)
        
        # 2. 查询数据库缓存
        cached_data = self._get_from_db(xq_symbol)
        
        if cached_data:
            # 检查有效期
            updated_at = cached_data.get("_updated_at")
            if updated_at:
                try:
                    last_date = datetime.datetime.strptime(updated_at, "%Y-%m-%d").date()
                    days_diff = (datetime.date.today() - last_date).days
                    if days_diff < self.cache_validity_days:
                        # 缓存有效
                        return cached_data
                except ValueError:
                    pass # 日期格式错误，视为过期
        
        # 3. 如果只查缓存，或者没找到且only_cache=True，直接返回
        if only_cache:
            return {}

        # 4. 联网获取 (AkShare/Snowball)
        if ak is None:
            self.logger.error("AkShare not installed.")
            return {}

        self.logger.info(f"Fetching info for {query} ({xq_symbol}) from network...")
        try:
            df = ak.stock_individual_basic_info_xq(symbol=xq_symbol)
            if df is None or df.empty:
                return {}
            
            # 转换 DataFrame 为 Dict
            # 假设 df 列为: item, value
            data = dict(zip(df['item'], df['value']))
            
            # 添加内部字段
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            data["_updated_at"] = today_str
            data["_symbol"] = xq_symbol
            
            # 5. 存入数据库
            self._save_to_db(xq_symbol, today_str, data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching info for {xq_symbol}: {e}")
            return {}

    def _get_from_db(self, symbol: str) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT data, updated_at FROM stock_detail WHERE symbol=?", (symbol,))
                row = c.fetchone()
                if row:
                    data_json, updated_at = row
                    data = json.loads(data_json)
                    data["_updated_at"] = updated_at # 注入时间方便上层判断
                    return data
        except Exception as e:
            self.logger.error(f"DB Read Error: {e}")
        return None

    def _save_to_db(self, symbol: str, updated_at: str, data: Dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                data_json = json.dumps(data, ensure_ascii=False)
                c.execute('''
                    INSERT OR REPLACE INTO stock_detail (symbol, updated_at, data)
                    VALUES (?, ?, ?)
                ''', (symbol, updated_at, data_json))
                conn.commit()
        except Exception as e:
            self.logger.error(f"DB Write Error: {e}")

    # --- 接口兼容 ---
    def get_price(self, code: str, date: str) -> float: return None 
    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame: return pd.DataFrame()
    def get_table(self, table_name: str, date: str = None) -> pd.DataFrame: return pd.DataFrame()
    def get_snapshot(self, codes: list) -> list: return []