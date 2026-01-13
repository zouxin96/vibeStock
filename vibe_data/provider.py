from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional
import logging
from enum import Enum
import os

class FetcherType(Enum):
    POST_MARKET = "post_market"
    REALTIME = "realtime"

class DataCategory(Enum):
    STOCK = "stock"
    INFO = "info"

class DataDimension(Enum):
    DATE = "date"
    STOCK = "stock"
    INFO = "info"
    OTHER = "other"

class IDataProvider(ABC):
    """
    Abstract interface for data providers.
    """
    
    @property
    @abstractmethod
    def data_dimension(self) -> DataDimension:
        """Dimension of data organization (e.g., by DATE, by STOCK)"""
        pass

    @property
    @abstractmethod
    def archive_filename_template(self) -> str:
        """Template for filename, e.g. 'daily_{date}.csv'"""
        pass

    def get_archive_filename(self, **kwargs) -> str:
        """Generate filename from template"""
        return self.archive_filename_template.format(**kwargs)

    @abstractmethod
    def get_price(self, code: str, date: str) -> Optional[float]:
        """Get single price for a stock on a date"""
        pass

    @abstractmethod
    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get history bars (Open, High, Low, Close, Vol)"""
        pass
        
    @abstractmethod
    def get_table(self, table_name: str, date: Optional[str] = None) -> pd.DataFrame:
        """Generic method to get a specific data table (e.g., 'daily_basic', 'dragon_tiger')"""
        pass

class BaseFetcher(IDataProvider):
    """
    Base class for fetchers with logging and type handling.
    """
    def __init__(self, fetcher_type: FetcherType):
        self.fetcher_type = fetcher_type
        self.logger = logging.getLogger(f"vibe.data.{self.__class__.__name__.lower()}")

    @property
    def data_dimension(self) -> DataDimension:
        # Default to OTHER, override in subclasses
        return DataDimension.OTHER

    @property
    def archive_filename_template(self) -> str:
        # Default template
        return "{date}.csv"

    def log(self, level, msg, *args, **kwargs):
        """
        Custom logging logic:
        - Realtime: Only log ERROR or CRITICAL.
        - PostMarket: Log everything (subject to global level).
        """
        if self.fetcher_type == FetcherType.REALTIME:
            if level >= logging.ERROR:
                self.logger.log(level, msg, *args, **kwargs)
        else:
            self.logger.log(level, msg, *args, **kwargs)

    def get_save_path(self, category: DataCategory, filename: str) -> str:
        """
        Generate save path based on category and fetcher type.
        Structure: data/storage/{category}/{fetcher_type}/{filename}
        """
        # category.value -> "stock" or "info"
        # self.fetcher_type.value -> "post_market" or "realtime"
        path = os.path.join("data", "storage", category.value, self.fetcher_type.value)
        if not os.path.exists(path):
            os.makedirs(path)
        return os.path.join(path, filename)
