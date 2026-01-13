from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional

class IDataProvider(ABC):
    """
    Abstract interface for data providers.
    """
    
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
