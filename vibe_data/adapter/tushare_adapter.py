from ..provider import BaseFetcher, FetcherType, DataCategory, DataDimension
import tushare as ts
import pandas as pd
import os
import datetime
import logging

class TushareAdapter(BaseFetcher):
    def __init__(self, token: str):
        super().__init__(FetcherType.POST_MARKET)
        self.token = token
        if self.token and self.token != "YOUR_TUSHARE_TOKEN":
            try:
                self.pro = ts.pro_api(self.token)
                self.log(logging.INFO, "Tushare Pro API initialized.")
            except Exception as e:
                self.log(logging.ERROR, f"Failed to init Tushare Pro: {e}")
                self.pro = None
        else:
            self.log(logging.WARNING, "Tushare token not configured. Some features may not work.")
            self.pro = None
        
        # self.data_dir is no longer needed as we use get_save_path

    @property
    def data_dimension(self) -> DataDimension:
        return DataDimension.DATE

    @property
    def archive_filename_template(self) -> str:
        return "daily_{date}.csv"

    def get_price(self, code, date):
        # Implementation for single price check if needed
        return None

    def get_snapshot(self, codes: list) -> list:
        # Tushare doesn't strictly have a "realtime snapshot" free API as fast as Sina.
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
            self.log(logging.ERROR, f"Failed to fetch ths_index: {e}")
            return pd.DataFrame()

    def get_concept(self):
        """
        Fetch standard Tushare concepts.
        """
        if not self.pro:
            return pd.DataFrame()
        try:
            return self.pro.concept()
        except Exception as e:
            self.log(logging.ERROR, f"Failed to fetch concept: {e}")
            return pd.DataFrame()

    def get_index_classify(self, level='L1', src='SW2021'):
        """
        Fetch industry classifications (e.g., Shenwan).
        src: 'SW2014', 'SW2021'
        level: 'L1', 'L2', 'L3'
        """
        if not self.pro:
            return pd.DataFrame()
        try:
            return self.pro.index_classify(level=level, src=src)
        except Exception as e:
            self.log(logging.ERROR, f"Failed to fetch index_classify: {e}")
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
            self.log(logging.ERROR, f"Failed to fetch ths_member for {ts_code}: {e}")
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
                self.log(logging.WARNING, "get_income requires either ts_code or period")
                return pd.DataFrame()
        except Exception as e:
            self.log(logging.ERROR, f"Failed to fetch income data: {e}")
            return pd.DataFrame()

    def sync_daily_data(self, start_date: str = None, end_date: str = None):
        """
        Synchronize daily data for the market.
        If start_date/end_date provided (YYYYMMDD), syncs that range.
        Otherwise syncs today.
        """
        if not self.pro:
            self.log(logging.ERROR, "Cannot sync: Tushare token invalid.")
            return

        dates_to_sync = []
        if start_date and end_date:
            try:
                dt_range = pd.date_range(start=start_date, end=end_date)
                dates_to_sync = [d.strftime("%Y%m%d") for d in dt_range]
            except Exception as e:
                self.log(logging.ERROR, f"Invalid date range: {e}")
                return
        elif start_date:
             dates_to_sync = [start_date]
        else:
            dates_to_sync = [datetime.datetime.now().strftime("%Y%m%d")]

        self.log(logging.INFO, f"Starting Tushare sync for {len(dates_to_sync)} days...")
        
        for date_str in dates_to_sync:
            try:
                self.log(logging.INFO, f"Fetching Tushare daily for {date_str}...")
                # 1. Get daily data
                df = self.pro.daily(trade_date=date_str)
                
                if df.empty:
                    self.log(logging.WARNING, f"No data found for {date_str}. Market might be closed.")
                else:
                    # Save to CSV
                    # Use template to generate filename
                    fname = self.get_archive_filename(date=date_str)
                    filename = self.get_save_path(DataCategory.STOCK, fname)
                    df.to_csv(filename, index=False)
                    self.log(logging.INFO, f"Successfully synced {len(df)} records to {filename}")
            except Exception as e:
                self.log(logging.ERROR, f"Error during Tushare sync for {date_str}: {e}")
                # Continue to next day even if one fails
                continue
        
        self.log(logging.INFO, "Tushare sync batch completed.")