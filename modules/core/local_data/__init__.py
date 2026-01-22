from vibe_core.module import VibeModule, ModuleCategory
from vibe_core.data.provider import IDataProvider, DataDimension, SyncPolicy
import pandas as pd
import os
import re
from typing import Optional, Dict

class LocalDataModule(VibeModule, IDataProvider):
    """
    Local Data Module
    Reads data from local Markdown/CSV files.
    Replaces LocalFileAdapter.
    """
    
    def __init__(self, context=None):
        VibeModule.__init__(self)
        self.category = ModuleCategory.DATA
        self.name = "local_data"
        self.description = "Local File Data Provider"
        
        self.root_path = "tushare" # Default
        
        # Mapping logical names to partial filenames
        self.file_map = {
            "daily": "27_历史日线",
            "weekly": "144_周线行情",
            "dragon_tiger_daily": "106_龙虎榜每日统计单",
            "stock_list": "25_股票列表",
        }

    def initialize(self, context):
        self.context = context
        
        # Check config for root path override
        # if self.context.config ...
        
        if self.context.data and hasattr(self.context.data, 'register_provider'):
             self.context.data.register_provider("local", self)
        
        self.configure()
        self.on_start()

    def configure(self):
        self.context.logger.info(f"{self.name} initialized.")

    @property
    def data_dimension(self) -> DataDimension:
        return DataDimension.HISTORY

    @property
    def sync_policy(self) -> SyncPolicy:
        return SyncPolicy.MANUAL

    def _find_file(self, keyword: str) -> Optional[str]:
        if not os.path.exists(self.root_path):
            return None
            
        for f in os.listdir(self.root_path):
            if keyword in f:
                return os.path.join(self.root_path, f)
        return None

    def _read_markdown_table(self, file_path: str) -> pd.DataFrame:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            data = []
            headers = []
            
            for line in lines:
                line = line.strip()
                if not line.startswith("|"): continue
                
                row = [c.strip() for c in line.split('|') if c]
                if not row: continue
                    
                if not headers:
                    headers = row
                elif '---' in row[0]: continue
                else:
                    data.append(row)
            
            if not headers: return pd.DataFrame()
            return pd.DataFrame(data, columns=headers)
            
        except Exception as e:
            self.context.logger.error(f"Error reading {file_path}: {e}")
            return pd.DataFrame()

    def get_price(self, code: str, date: str) -> Optional[float]:
        df = self.get_table("daily")
        if df.empty: return None
        
        # Naive implementation
        try:
            row = df[(df['ts_code'] == code) & (df['trade_date'] == date)]
            if not row.empty:
                return float(row.iloc[0]['close'])
        except: pass
        return None

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        df = self.get_table("daily")
        if df.empty: return pd.DataFrame()
        try:
            mask = (df['ts_code'] == code) & (df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)
            return df[mask]
        except: return pd.DataFrame()

    def get_table(self, table_name: str, date: Optional[str] = None) -> pd.DataFrame:
        keyword = self.file_map.get(table_name, table_name)
        file_path = self._find_file(keyword)
        
        if not file_path:
            file_path = self._find_file(table_name)
        
        if file_path:
            return self._read_markdown_table(file_path)
        else:
            return pd.DataFrame()
    
    def get_snapshot(self, codes): return []
