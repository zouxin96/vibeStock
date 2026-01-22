from vibe_core.module import VibeModule, ModuleCategory
from vibe_core.data.provider import BaseFetcher, FetcherType, DataCategory, DataDimension
import pandas as pd
import datetime
import logging

try:
    import tushare as ts
except ImportError:
    ts = None

class TushareDataModule(VibeModule, BaseFetcher):
    """
    Tushare Data Module
    Consolidates TushareAdapter and TushareInfoAdapter functionality.
    """
    
    def __init__(self, context=None):
        VibeModule.__init__(self)
        BaseFetcher.__init__(self, FetcherType.POST_MARKET)
        
        self.category = ModuleCategory.DATA
        self.name = "tushare_data"
        self.description = "Tushare Data Provider (Market & Info)"
        self.pro = None
        self.token = ""

    def initialize(self, context):
        self.context = context
        
        # Get token from config
        # config structure: data: { tushare_token: "..." }
        if self.context.config:
            self.token = self.context.config.get("data", {}).get("tushare_token", "")
            
        self._init_tushare()
        
        # Register as "tushare" AND "tushare_info" to maintain backward routing compatibility
        if self.context.data and hasattr(self.context.data, 'register_provider'):
             self.context.data.register_provider("tushare", self)
             self.context.data.register_provider("tushare_info", self)
        
        self.configure()
        self.on_start()

    def configure(self):
        self.context.logger.info(f"{self.name} initialized.")

    def _init_tushare(self):
        if ts is None:
            self.context.logger.error("Tushare module not found. Please install tushare.")
            return

        if self.token and self.token != "YOUR_TUSHARE_TOKEN":
            try:
                self.pro = ts.pro_api(self.token)
                self.context.logger.info("Tushare Pro API initialized.")
            except Exception as e:
                self.context.logger.error(f"Failed to init Tushare Pro: {e}")
                self.pro = None
        else:
            self.context.logger.warning("Tushare token not configured.")
            self.pro = None

    @property
    def data_dimension(self) -> DataDimension:
        return DataDimension.DATE

    @property
    def archive_filename_template(self) -> str:
        # We need to handle dynamic templates if possible, or default to one
        # This is used by BaseFetcher.get_save_path logic usually passed from outside
        return "daily_{date}.csv"

    # --- IDataProvider Implementation ---

    def get_price(self, code, date=None):
        return None

    def get_snapshot(self, codes: list) -> list:
        return []
        
    def get_history(self, code, start_date, end_date):
        return pd.DataFrame()
        
    def get_table(self, table_name, date=None):
        return pd.DataFrame()

    # --- Tushare Specific Methods ---

    def get_ths_index(self, exchange='A', type='N'):
        if not self.pro: return pd.DataFrame()
        try:
            return self.pro.ths_index(exchange=exchange, type=type)
        except Exception as e:
            self.context.logger.error(f"Failed to fetch ths_index: {e}")
            return pd.DataFrame()

    def get_concept(self):
        if not self.pro: return pd.DataFrame()
        try:
            return self.pro.concept()
        except Exception as e:
            self.context.logger.error(f"Failed to fetch concept: {e}")
            return pd.DataFrame()

    def get_index_classify(self, level='L1', src='SW2021'):
        if not self.pro: return pd.DataFrame()
        try:
            return self.pro.index_classify(level=level, src=src)
        except Exception as e:
            self.context.logger.error(f"Failed to fetch index_classify: {e}")
            return pd.DataFrame()

    def get_ths_member(self, ts_code):
        if not self.pro: return pd.DataFrame()
        try:
            return self.pro.ths_member(ts_code=ts_code)
        except Exception as e:
            self.context.logger.error(f"Failed to fetch ths_member for {ts_code}: {e}")
            return pd.DataFrame()

    def get_income(self, ts_code=None, period=None, start_date=None, end_date=None):
        if not self.pro: return pd.DataFrame()
        try:
            if ts_code:
                return self.pro.income(ts_code=ts_code, period=period, start_date=start_date, end_date=end_date)
            elif period:
                return self.pro.income_vip(period=period)
            else:
                self.context.logger.warning("get_income requires either ts_code or period")
                return pd.DataFrame()
        except Exception as e:
            self.context.logger.error(f"Failed to fetch income data: {e}")
            return pd.DataFrame()

    def sync_daily_data(self, start_date: str = None, end_date: str = None):
        if not self.pro:
            self.context.logger.error("Cannot sync: Tushare token invalid.")
            return

        dates_to_sync = []
        if start_date and end_date:
            try:
                dt_range = pd.date_range(start=start_date, end=end_date)
                dates_to_sync = [d.strftime("%Y%m%d") for d in dt_range]
            except Exception as e:
                self.context.logger.error(f"Invalid date range: {e}")
                return
        elif start_date:
             dates_to_sync = [start_date]
        else:
            dates_to_sync = [datetime.datetime.now().strftime("%Y%m%d")]

        self.context.logger.info(f"Starting Tushare sync for {len(dates_to_sync)} days...")
        
        for date_str in dates_to_sync:
            try:
                self.context.logger.info(f"Fetching Tushare daily for {date_str}...")
                df = self.pro.daily(trade_date=date_str)
                
                if df.empty:
                    self.context.logger.warning(f"No data found for {date_str}. Market might be closed.")
                else:
                    fname = f"daily_{date_str}.csv"
                    # We access BaseFetcher.get_save_path but need to ensure 'stock' category logic
                    # BaseFetcher.get_save_path(category, filename)
                    filename = self.get_save_path(DataCategory.STOCK, fname)
                    df.to_csv(filename, index=False)
                    self.context.logger.info(f"Successfully synced {len(df)} records to {filename}")
            except Exception as e:
                self.context.logger.error(f"Error during Tushare sync for {date_str}: {e}")
                continue
        
        self.context.logger.info("Tushare sync batch completed.")

    # --- Info Adapter Methods ---

    def get_concept_list(self, src="ths"):
        if not self.pro: return pd.DataFrame()
        try:
            if src == "ths":
                return self.pro.ths_index(exchange="A", type="N")
            elif src == "ts":
                return self.pro.concept()
            elif src == "dc":
                today = datetime.datetime.now().strftime("%Y%m%d")
                return self.pro.dc_index(trade_date=today)
            else:
                self.context.logger.warning(f"Unknown source {src}")
                return pd.DataFrame()
        except Exception as e:
            self.context.logger.error(f"Failed to fetch concept list ({src}): {e}")
            return pd.DataFrame()

    def get_concept_detail(self, id: str, src="ths"):
        if not self.pro: return pd.DataFrame()
        try:
            if src == "ths":
                return self.pro.ths_member(ts_code=id)
            elif src == "ts":
                return self.pro.concept_detail(id=id)
            else:
                self.context.logger.warning("Only THS and TS supported for detail currently.")
                return pd.DataFrame()
        except Exception as e:
            self.context.logger.error(f"Failed to fetch concept detail {id}: {e}")
            return pd.DataFrame()
            
    def get_industry_list(self, src="SW2021", level="L1"):
        if not self.pro: return pd.DataFrame()
        try:
            return self.pro.index_classify(level=level, src=src)
        except Exception as e:
            self.context.logger.error(f"Failed to fetch industry list: {e}")
            return pd.DataFrame()

    def sync_all_concepts(self, src="ths"):
        self.context.logger.info(f"Syncing {src} concepts...")
        df = self.get_concept_list(src)
        if not df.empty:
            fname = f"concepts_{src}_{datetime.date.today()}.csv"
            filename = self.get_save_path(DataCategory.INFO, fname)
            df.to_csv(filename, index=False)
            self.context.logger.info(f"Saved {len(df)} concepts to {filename}")
        else:
            self.context.logger.warning(f"No concepts found for {src}")
