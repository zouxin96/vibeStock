from ..provider import BaseFetcher, FetcherType, DataCategory, DataDimension
import tushare as ts
import pandas as pd
import logging
import datetime

class TushareInfoAdapter(BaseFetcher):
    """
    Adapter for fetching Tushare Information Data (Concepts, Sectors, Lists).
    Separated from market data to manage API token usage and logic distinctness.
    """
    
    def __init__(self, token: str):
        super().__init__(FetcherType.POST_MARKET)
        self.token = token
        if self.token and self.token != "YOUR_TUSHARE_TOKEN":
            try:
                self.pro = ts.pro_api(self.token)
                self.log(logging.INFO, "Tushare Pro API (Info) initialized.")
            except Exception as e:
                self.log(logging.ERROR, f"Failed to init Tushare Pro (Info): {e}")
                self.pro = None
        else:
            self.log(logging.WARNING, "Tushare token not configured.")
            self.pro = None

    @property
    def data_dimension(self) -> DataDimension:
        return DataDimension.INFO

    @property
    def archive_filename_template(self) -> str:
        return "concepts_{src}_{date}.csv"

    # Required by BaseFetcher/IDataProvider but not primary use here
    def get_price(self, code, date): return None
    def get_snapshot(self, codes): return []
    def get_history(self, code, start, end): return pd.DataFrame()
    def get_table(self, table_name, date=None): return pd.DataFrame()

    def get_concept_list(self, src="ths"):
        """
        Get list of concepts.
        src: "ths" (TongHuaShun), "ts" (Tushare Standard), "dc" (EastMoney/DongCai)
        """
        if not self.pro: return pd.DataFrame()
        
        try:
            if src == "ths":
                # type='N' for concepts
                return self.pro.ths_index(exchange="A", type="N")
            elif src == "ts":
                return self.pro.concept()
            elif src == "dc":
                # dc_index needs a date usually, but maybe we can just get latest?
                # The doc says "trade_date" is optional in params table but example uses it.
                # Let's try fetching for today or yesterday.
                today = datetime.datetime.now().strftime("%Y%m%d")
                return self.pro.dc_index(trade_date=today)
            else:
                self.log(logging.WARNING, f"Unknown source {src}")
                return pd.DataFrame()
        except Exception as e:
            self.log(logging.ERROR, f"Failed to fetch concept list ({src}): {e}")
            return pd.DataFrame()

    def get_concept_detail(self, id: str, src="ths"):
        """
        Get members of a concept.
        id: concept code (e.g., '885800.TI')
        """
        if not self.pro: return pd.DataFrame()
        
        try:
            if src == "ths":
                return self.pro.ths_member(ts_code=id)
            elif src == "ts":
                return self.pro.concept_detail(id=id)
            else:
                self.log(logging.WARNING, "Only THS and TS supported for detail currently.")
                return pd.DataFrame()
        except Exception as e:
            self.log(logging.ERROR, f"Failed to fetch concept detail {id}: {e}")
            return pd.DataFrame()
            
    def get_industry_list(self, src="SW2021", level="L1"):
        """
        Get industry classification.
        src: 'SW2021', 'SW2014'
        """
        if not self.pro: return pd.DataFrame()
        try:
            return self.pro.index_classify(level=level, src=src)
        except Exception as e:
            self.log(logging.ERROR, f"Failed to fetch industry list: {e}")
            return pd.DataFrame()

    def sync_all_concepts(self, src="ths"):
        """
        Sync all concept lists and save to storage.
        """
        self.log(logging.INFO, f"Syncing {src} concepts...")
        df = self.get_concept_list(src)
        if not df.empty:
            # Use template for filename
            fname = self.get_archive_filename(src=src, date=datetime.date.today())
            filename = self.get_save_path(DataCategory.INFO, fname)
            df.to_csv(filename, index=False)
            self.log(logging.INFO, f"Saved {len(df)} concepts to {filename}")
        else:
            self.log(logging.WARNING, f"No concepts found for {src}")
