import pandas as pd
from typing import Optional, List
import logging
from .market import AKShareMarket
from .meta import AKShareMeta
from .limit_board import AKShareLimitBoard
import akshare as ak

# 使用 Mixin 模式或者 Facade 模式组合
# 这里采用多重继承 (Mixin)，简单直接
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
                if date and 'date' in func.__code__.co_varnames:
                    return func(date=date)
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
        # 注意: 原来的 sync_daily_data 逻辑在旧文件中，现在重写。
        import datetime
        import os
        from ...provider import DataCategory
        
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
