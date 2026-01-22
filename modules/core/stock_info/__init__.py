from vibe_core.module import VibeModule, ModuleCategory
from vibe_core.data.provider import IDataProvider, DataDimension, SyncPolicy
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

class StockInfoModule(VibeModule, IDataProvider):
    """
    Stock Info Module (SQLite Backend)
    Provides detailed stock information (e.g., sector, province) with caching.
    Replaces StockInfoAdapter.
    """
    
    def __init__(self, context=None):
        VibeModule.__init__(self)
        self.category = ModuleCategory.DATA
        self.name = "stock_info"
        self.description = "Detailed Stock Info Provider (SQLite Cache)"
        self.logger = logging.getLogger("vibe.data.stock_info")
        
        self.db_path = "data/storage/stock_info.db"
        self.cache_validity_days = 30
        self._code_name_map = None

    def initialize(self, context):
        self.context = context
        if context and hasattr(context, 'logger'):
            self.logger = context.logger
        
        # Initialize DB
        self._init_db()
        
        # Register provider
        if self.context.data and hasattr(self.context.data, 'register_provider'):
             self.context.data.register_provider("stock_info", self)
        
        self.configure()
        self.on_start()

    def configure(self):
        self.context.logger.info(f"{self.name} initialized.")

    def _init_db(self):
        """Initialize database schema"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute('''
                    CREATE TABLE IF NOT EXISTS stock_detail (
                        symbol TEXT PRIMARY KEY,
                        updated_at TEXT,
                        data TEXT
                    )
                ''')
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
        code = str(code)
        if code.startswith("SH") or code.startswith("SZ") or code.startswith("BJ"):
            return code
        
        if code.startswith("6"):
            return f"SH{code}"
        elif code.startswith("0") or code.startswith("3"):
            return f"SZ{code}"
        elif code.startswith("4") or code.startswith("8"):
            return f"BJ{code}"
        return f"SH{code}" 

    def get_stock_info(self, query: str, only_cache: bool = False) -> Dict[str, Any]:
        self._ensure_code_map()
        code = self._code_name_map.get(query) or self._code_name_map.get(str(query))
        
        if not code and (str(query).isdigit() or str(query).startswith(('SH', 'SZ', 'BJ'))):
            code = query
            
        if not code:
            return {}

        xq_symbol = self._format_symbol_for_xq(code)
        
        # Check cache
        cached_data = self._get_from_db(xq_symbol)
        
        if cached_data:
            updated_at = cached_data.get("_updated_at")
            if updated_at:
                try:
                    last_date = datetime.datetime.strptime(updated_at, "%Y-%m-%d").date()
                    days_diff = (datetime.date.today() - last_date).days
                    if days_diff < self.cache_validity_days:
                        return cached_data
                except ValueError:
                    pass 
        
        if only_cache:
            return {}

        # Fetch from network
        if ak is None:
            self.logger.error("AkShare not installed.")
            return {}

        self.logger.info(f"Fetching info for {query} ({xq_symbol}) from network...")
        try:
            df = ak.stock_individual_basic_info_xq(symbol=xq_symbol)
            if df is None or df.empty:
                return {}
            
            data = dict(zip(df['item'], df['value']))
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            data["_updated_at"] = today_str
            data["_symbol"] = xq_symbol
            
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
                    data["_updated_at"] = updated_at
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

    # --- IDataProvider Stubs ---
    def get_price(self, code: str, date: str = None) -> float: return None 
    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame: return pd.DataFrame()
    def get_table(self, table_name: str, date: str = None) -> pd.DataFrame: return pd.DataFrame()
    def get_snapshot(self, codes: list) -> list: return []

    def on_event(self, event):
        """No-op for data provider."""
        pass
