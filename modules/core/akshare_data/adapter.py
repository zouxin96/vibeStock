import pandas as pd
import logging
from realtime.market import AKShareMarket
from realtime.limit import AKShareLimitBoard
from dictionary.meta import AKShareMeta

try:
    import akshare as ak
except ImportError:
    ak = None

class AKShareAdapter(AKShareMarket, AKShareMeta, AKShareLimitBoard):
    """
    统一的 AKShare 适配器，集成了 Market, Meta, LimitBoard 等功能。
    对外保持兼容。
    """
    
    def get_table(self, table_name: str, date: str = None) -> pd.DataFrame:
        """
        通用后备方法，允许直接调用 akshare 的任意函数。
        """
        self._ensure_akshare()
        try:
            if hasattr(ak, table_name):
                func = getattr(ak, table_name)
                # Simple introspection for 'date' param
                # Note: akshare functions have varying signatures.
                # This is a best-effort helper.
                if date:
                    try:
                        return func(date=date)
                    except TypeError:
                        return func()
                else:
                    return func()
            else:
                self.log(logging.WARNING, f"AKShare 没有函数 '{table_name}'")
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_table '{table_name}' 错误: {e}")
        
        return pd.DataFrame()

    def sync_daily_data(self):
        """
        复用 Market 的 full_snapshot 来实现 sync_daily_data
        """
        import datetime
        import os
        from vibe_core.data.provider import DataCategory
        
        today = datetime.datetime.now().strftime("%Y%m%d")
        fname = self.get_archive_filename(date=today)
        filename = self.get_save_path(DataCategory.STOCK, fname)
        
        if os.path.exists(filename):
            self.log(logging.INFO, f"今日数据已存在: {filename}")
            return
            
        self.log(logging.INFO, f"开始同步 {today} 全市场数据...")
        df = self.get_full_snapshot()
        if not df.empty:
            df.to_csv(filename, index=False)
            self.log(logging.INFO, f"同步完成: {len(df)} 条")