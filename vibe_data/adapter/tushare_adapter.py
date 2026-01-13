from ..provider import IDataProvider
import tushare as ts
import pandas as pd
import os
import datetime
import logging

logger = logging.getLogger("vibe.data.tushare")

class TushareAdapter(IDataProvider):
    def __init__(self, token: str):
        self.token = token
        if self.token and self.token != "YOUR_TUSHARE_TOKEN":
            try:
                self.pro = ts.pro_api(self.token)
                logger.info("Tushare Pro API initialized.")
            except Exception as e:
                logger.error(f"Failed to init Tushare Pro: {e}")
                self.pro = None
        else:
            logger.warning("Tushare token not configured. Some features may not work.")
            self.pro = None
        
        # Ensure data directory exists
        self.data_dir = os.path.join("data", "daily")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_price(self, code, date):
        # Implementation for single price check if needed
        return None

    def get_snapshot(self, codes: list) -> list:
        # Tushare doesn't strictly have a "realtime snapshot" free API as fast as Sina.
        # But we can implement it via `get_realtime_quotes` if we use the old interface,
        # or just return empty and let Sina handle realtime.
        return []
        
    def get_history(self, code, start_date, end_date):
        # Read from local file if synced, else fetch?
        # For this task, we focus on the sync method.
        return pd.DataFrame()
        
    def get_table(self, table_name, date=None):
        return pd.DataFrame()

    def get_ths_index(self, exchange='A', type='N'):
        """
        Fetch THS concepts/indices.
        Requires 6000 points.
        """
        if not self.pro:
            return pd.DataFrame()
        try:
            return self.pro.ths_index(exchange=exchange, type=type)
        except Exception as e:
            logger.error(f"Failed to fetch ths_index: {e}")
            return pd.DataFrame()

    def get_ths_member(self, ts_code):
        """
        Fetch members of a THS concept/index.
        Requires 6000 points.
        """
        if not self.pro:
            return pd.DataFrame()
        try:
            return self.pro.ths_member(ts_code=ts_code)
        except Exception as e:
            logger.error(f"Failed to fetch ths_member for {ts_code}: {e}")
            return pd.DataFrame()

    def get_income(self, ts_code=None, period=None, start_date=None, end_date=None):
        """
        Fetch income statement.
        If ts_code is provided, uses `income` (2000 points).
        If ts_code is NOT provided and period is, uses `income_vip` (5000 points).
        """
        if not self.pro:
            return pd.DataFrame()
        
        try:
            if ts_code:
                return self.pro.income(ts_code=ts_code, period=period, start_date=start_date, end_date=end_date)
            elif period:
                # Batch fetch for a period
                return self.pro.income_vip(period=period)
            else:
                logger.warning("get_income requires either ts_code or period")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to fetch income data: {e}")
            return pd.DataFrame()

    def sync_daily_data(self):
        """
        Synchronize daily data for the market.
        Running at 16:00 means we want today's data.
        """
        if not self.pro:
            logger.error("Cannot sync: Tushare token invalid.")
            return

        today = datetime.datetime.now().strftime("%Y%m%d")
        logger.info(f"Starting Tushare sync for {today}...")
        
        try:
            # 1. Get stock list (limit to a few for demo/safety if full list is huge)
            # For a real app, we might want all. For now, let's just get the daily data 
            # for the whole market using `daily` interface which supports `trade_date`.
            
            df = self.pro.daily(trade_date=today)
            
            if df.empty:
                logger.warning(f"No data found for {today}. Market might be closed or data not ready.")
            else:
                # Save to CSV
                filename = os.path.join(self.data_dir, f"daily_{today}.csv")
                df.to_csv(filename, index=False)
                logger.info(f"Successfully synced {len(df)} records to {filename}")
                
        except Exception as e:
            logger.error(f"Error during Tushare sync: {e}")
