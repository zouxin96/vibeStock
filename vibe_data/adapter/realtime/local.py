import pandas as pd
import os
import re
from typing import Optional, Dict
from ...provider import IDataProvider, DataDimension, SyncPolicy

class LocalFileAdapter(IDataProvider):
    """
    Reads data from local Markdown/CSV files in the 'tushare/' directory.
    """
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        # Mapping logical names to partial filenames
        self.file_map = {
            "daily": "27_历史日线",
            "weekly": "144_周线行情",
            "dragon_tiger_daily": "106_龙虎榜每日统计单",
            "stock_list": "25_股票列表",
            # Add more mappings as needed based on the file list
        }

    @property
    def data_dimension(self) -> DataDimension:
        return DataDimension.HISTORY

    @property
    def sync_policy(self) -> SyncPolicy:
        return SyncPolicy.MANUAL

    def _find_file(self, keyword: str) -> Optional[str]:
        """Finds the full filename containing the keyword"""
        if not os.path.exists(self.root_path):
            return None
            
        for f in os.listdir(self.root_path):
            if keyword in f:
                return os.path.join(self.root_path, f)
        return None

    def _read_markdown_table(self, file_path: str) -> pd.DataFrame:
        """
        Parses a markdown table into a Pandas DataFrame.
        Assumes the file contains a standard MD table.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Simple parser for pipe-separated tables
            data = []
            headers = []
            
            for line in lines:
                line = line.strip()
                if not line.startswith("|"):
                    continue
                
                # Split by pipe and strip whitespace
                row = [c.strip() for c in line.split('|') if c]
                
                if not row:
                    continue
                    
                if not headers:
                    headers = row
                elif '---' in row[0]: # Separator line
                    continue
                else:
                    data.append(row)
            
            if not headers:
                return pd.DataFrame()
                
            return pd.DataFrame(data, columns=headers)
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return pd.DataFrame()

    def get_price(self, code: str, date: str) -> Optional[float]:
        # Implementation would require efficient indexing which MD files don't support well.
        # This is a naive implementation.
        df = self.get_table("daily")
        if df.empty:
            return None
        
        # Assuming columns exist (this depends on the actual file content)
        # We might need to map column names too.
        row = df[(df['ts_code'] == code) & (df['trade_date'] == date)]
        if not row.empty:
            return float(row.iloc[0]['close'])
        return None

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        df = self.get_table("daily")
        if df.empty:
            return pd.DataFrame()
            
        # Filter (Naive string comparison for dates YYYYMMDD)
        # Note: This loads the WHOLE file into memory. inefficient but functional for small files.
        mask = (df['ts_code'] == code) & (df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)
        return df[mask]

    def get_table(self, table_name: str, date: Optional[str] = None) -> pd.DataFrame:
        keyword = self.file_map.get(table_name, table_name)
        file_path = self._find_file(keyword)
        
        if not file_path:
            # Try searching directly if not in map
            file_path = self._find_file(table_name)
        
        if file_path:
            return self._read_markdown_table(file_path)
        else:
            print(f"Table/File not found for: {table_name}")
            return pd.DataFrame()
