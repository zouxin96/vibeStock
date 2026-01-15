import pandas as pd
import logging
import datetime
import os
from .base import AKShareBase
import akshare as ak

class AKShareLimitBoard(AKShareBase):
    """
    负责涨跌停、炸板数据。
    逻辑从 LimitBoardAdapter 迁移并复用 AKShareBase。
    """

    def get_limit_up_pool(self, date: str = None) -> pd.DataFrame:
        self._ensure_akshare()
        date_str = date if date else datetime.datetime.now().strftime("%Y%m%d")
        try:
            return ak.stock_zt_pool_em(date=date_str)
        except Exception as e:
            self.log(logging.ERROR, f"Error fetching limit up pool: {e}")
            return pd.DataFrame()

    def get_broken_limit_pool(self, date: str = None) -> pd.DataFrame:
        self._ensure_akshare()
        date_str = date if date else datetime.datetime.now().strftime("%Y%m%d")
        try:
            return ak.stock_zt_pool_zbgc_em(date=date_str)
        except Exception as e:
            self.log(logging.ERROR, f"Error fetching broken limit pool: {e}")
            return pd.DataFrame()

    def get_limit_down_pool(self, date: str = None) -> pd.DataFrame:
        self._ensure_akshare()
        date_str = date if date else datetime.datetime.now().strftime("%Y%m%d")
        try:
            return ak.stock_dt_pool_em(date=date_str)
        except Exception as e:
            self.log(logging.ERROR, f"Error fetching limit down pool: {e}")
            return pd.DataFrame()

    def sync_limit_data(self, date: str = None):
        """同步并保存当天的涨跌停数据。"""
        date_str = date if date else datetime.datetime.now().strftime("%Y%m%d")
        save_dir = os.path.join("data", "storage", "limit_board", date_str)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        zt_df = self.get_limit_up_pool(date_str)
        zb_df = self.get_broken_limit_pool(date_str)
        dt_df = self.get_limit_down_pool(date_str)
        
        merged = pd.DataFrame()
        if not zt_df.empty:
            zt_df['status'] = 'limit_up'
            merged = pd.concat([merged, zt_df])
        if not zb_df.empty:
            zb_df['status'] = 'broken'
            merged = pd.concat([merged, zb_df])
            
        if not merged.empty:
            merged = merged.drop_duplicates(subset=['代码'], keep='first')
            merged.to_csv(os.path.join(save_dir, "limit_up_combined.csv"), index=False)
            
        if not dt_df.empty:
            dt_df.to_csv(os.path.join(save_dir, "limit_down.csv"), index=False)
