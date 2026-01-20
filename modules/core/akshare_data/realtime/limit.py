import pandas as pd
import logging
import datetime
import os
from ..base import AKShareBase
from vibe_data.debug_logger import log_debug, log_error

try:
    import akshare as ak
except ImportError:
    ak = None

class AKShareLimitBoard(AKShareBase):
    """
    负责涨跌停、炸板数据。
    逻辑从 LimitBoardAdapter 迁移并复用 AKShareBase。
    """

    def get_limit_up_pool(self, date: str = None) -> pd.DataFrame:
        self._ensure_akshare()
        log_debug(f"get_limit_up_pool called. Date={date}, AK_Loaded={ak is not None}")
        
        if ak is None: 
            log_debug("AKShare is None, returning empty DF")
            return pd.DataFrame()
        
        # 如果未指定日期，默认为当天
        now = datetime.datetime.now()
        is_today = (date is None) or (date == now.strftime("%Y%m%d"))
        date_str = date if date else now.strftime("%Y%m%d")
        
        try:
            df = ak.stock_zt_pool_em(date=date_str)
            if df is None:
                log_debug("ak.stock_zt_pool_em returned None! Returning empty DF.")
                return pd.DataFrame()
            
            log_debug(f"ak.stock_zt_pool_em returned DF with shape {df.shape}")
            
            # --- 自动备份逻辑 ---
            # 只要数据不为空就备份
            if not df.empty:
                try:
                    # 路径: data/storage/limit_backup/{date_str}/limit_up_{date_str}_{HHMMSS}.csv
                    save_dir = os.path.join("data", "storage", "limit_backup", date_str)
                    if not os.path.exists(save_dir):
                        os.makedirs(save_dir, exist_ok=True)
                        
                    timestamp_str = now.strftime("%H%M%S")
                    filename = f"limit_up_{date_str}_{timestamp_str}.csv"
                    filepath = os.path.join(save_dir, filename)
                    
                    df.to_csv(filepath, index=False, encoding='utf-8-sig')
                except Exception as backup_e:
                    self.log(logging.ERROR, f"Failed to backup limit pool: {backup_e}")
            # --------------------

            return df
        except Exception as e:
            log_error(f"Error fetching limit up pool for {date_str}", e)
            self.log(logging.ERROR, f"Error fetching limit up pool: {e}")
            return pd.DataFrame()

    def get_broken_limit_pool(self, date: str = None) -> pd.DataFrame:
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()

        date_str = date if date else datetime.datetime.now().strftime("%Y%m%d")
        try:
            df = ak.stock_zt_pool_zbgc_em(date=date_str)
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            log_error("Error fetching broken limit pool", e)
            self.log(logging.ERROR, f"Error fetching broken limit pool: {e}")
            return pd.DataFrame()

    def get_limit_down_pool(self, date: str = None) -> pd.DataFrame:

        self._ensure_akshare()
        if ak is None: return pd.DataFrame()

        date_str = date if date else datetime.datetime.now().strftime("%Y%m%d")
        try:
            df = ak.stock_dt_pool_em(date=date_str)
            return df if df is not None else pd.DataFrame()
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