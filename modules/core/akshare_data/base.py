import logging
import pandas as pd
from typing import Optional, List
from vibe_core.data.provider import BaseFetcher, FetcherType, DataDimension

try:
    import akshare as ak
except ImportError:
    ak = None

class AKShareBase(BaseFetcher):
    """
    AKShare 基础类，提供通用工具方法和共享状态。
    所有子模块应继承此类或持有其实例。
    """
    def __init__(self):
        super().__init__(FetcherType.POST_MARKET)
        if ak is None:
            self.log(logging.ERROR, "AKShare 未安装。请运行 `pip install akshare` 进行安装。" )
    
    def _ensure_akshare(self):
        """确保 AKShare 模块已加载，否则抛出异常。"""
        if ak is None:
            raise ImportError("未找到 AKShare 模块。请通过 pip 安装它。" )

    @property
    def data_dimension(self) -> DataDimension:
        return DataDimension.DATE

    @property
    def archive_filename_template(self) -> str:
        return "akshare_{date}.csv"