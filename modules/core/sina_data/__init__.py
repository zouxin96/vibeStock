from vibe_core.module import VibeModule, ModuleCategory
from vibe_core.data.provider import BaseFetcher, FetcherType
import requests
import logging
from typing import Optional
import pandas as pd
import datetime

class SinaDataModule(VibeModule, BaseFetcher):
    """
    Sina Data Module
    Fetches realtime data from Sina Finance (Free, No Token).
    Replaces SinaLiveAdapter.
    """
    
    def __init__(self, context=None):
        VibeModule.__init__(self)
        BaseFetcher.__init__(self, FetcherType.REALTIME)
        
        self.category = ModuleCategory.DATA
        self.name = "sina_data"
        self.description = "Realtime Data Provider (Sina)"
        
        self.headers = {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
    def initialize(self, context):
        self.context = context
        # Register as "sina" provider
        if self.context.data and hasattr(self.context.data, 'register_provider'):
             self.context.data.register_provider("sina", self)
             
        # Also register as default if none set (logic in hybrid handles this partially, 
        # but here we can be explicit if needed, though Hybrid does it too)
        
        self.configure()
        self.on_start()

    def configure(self):
        self.context.logger.info(f"{self.name} initialized.")

    def get_price(self, code: str, date: str = None) -> Optional[float]:
        # ... (implementation simplified for brevity, following the same pattern as get_snapshot)
        return None

    def get_snapshot(self, codes: list) -> list:
        """
        Efficiently fetch multiple stocks at once.
        Returns a list of dicts.
        """
        sina_codes = [self._convert_code(c) for c in codes]
        url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
        
        results = []
        try:
            # self.log(logging.DEBUG, f"Fetching Sina data from: {url}")
            resp = requests.get(url, headers=self.headers, timeout=5)
            
            if resp.status_code != 200:
                self.log(logging.ERROR, f"Sina API returned status code {resp.status_code}")
                return []

            # Force GBK encoding for Sina
            resp.encoding = 'gbk'
            content = resp.text
            if not content or len(content) < 50:
                self.log(logging.WARNING, f"Sina API returned empty or short response: {content}")
                return []

            lines = content.split('\n')
            for line in lines:
                if '="' not in line: continue
                
                # Extract code
                try:
                    raw_code = line.split('=')[0].split('_str_')[1]
                    data_str = line.split('="')[1].strip('";')
                    
                    if not data_str:
                        self.log(logging.DEBUG, f"No data for code {raw_code}")
                        continue

                    parts = data_str.split(',')
                    if len(parts) > 30:
                        name = parts[0]
                        price = float(parts[3])
                        pre_close = float(parts[2])
                        change = (price - pre_close) / pre_close * 100 if pre_close > 0 else 0
                        
                        results.append({
                            "code": raw_code,
                            "name": name,
                            "price": price,
                            "change": round(change, 2),
                            "open": float(parts[1]),
                            "high": float(parts[4]),
                            "low": float(parts[5]),
                            "vol": float(parts[8])
                        })
                except Exception as line_err:
                    self.log(logging.ERROR, f"Error parsing line: {line[:50]}... Error: {line_err}")
            
            # self.log(logging.INFO, f"Successfully fetched {len(results)} stocks from Sina.")
        except Exception as e:
            self.log(logging.ERROR, f"Sina Batch error: {str(e)}")
            
        return results

    def _convert_code(self, code: str) -> str:
        # 600519.SH -> sh600519
        if '.' in code:
            num, suffix = code.split('.')
            return f"{suffix.lower()}{num}"
        return code

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        # Sina doesn't provide easy history API via this endpoint.
        # Returning empty for now as user focused on REALTIME.
        return pd.DataFrame()

    def get_table(self, table_name: str, date: str = None) -> pd.DataFrame:
        return pd.DataFrame()
        
    def get_ui_config(self):
        # Optional: Add a status widget for Sina
        return {
            "id": "sina_status",
            "component": "base-data-widget", # Reusing generic widget
            "title": "Sina Data Status",
            "default_col_span": "col-span-1",
            "config_default": {},
            "script_path": "" # None needed for generic
        }

    def on_event(self, event):
        """No-op for data provider."""
        pass
