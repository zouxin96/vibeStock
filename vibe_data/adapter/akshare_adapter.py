import pandas as pd
import logging
import datetime
from typing import Optional, List
from ..provider import IDataProvider

# Try to import akshare, but don't crash if missing (allow safe failure)
try:
    import akshare as ak
except ImportError:
    ak = None

logger = logging.getLogger("vibe.data.akshare")

class AKShareAdapter(IDataProvider):
    """
    Data Provider using AKShare (Open Source Financial Data).
    https://github.com/akfamily/akshare
    """
    
    def __init__(self, **kwargs):
        if ak is None:
            logger.error("AKShare is not installed. Please run `pip install akshare`.")
    
    def _ensure_akshare(self):
        if ak is None:
            raise ImportError("AKShare module not found. Please install it via pip.")

    def get_price(self, code: str, date: str = None) -> Optional[float]:
        """
        Get current price. AKShare's realtime interface usually returns a DataFrame.
        """
        self._ensure_akshare()
        try:
            # Using stock_zh_a_spot_em for realtime data
            # This returns all stocks, so it might be slow if just for one.
            # Ideally we cache this or use a more specific function if available.
            # specific stock quote: stock_zh_a_spot_em() filters? No, it returns all.
            # But stock_bid_ask_em might be specific?
            
            # For efficiency in this specific method, maybe we just return None and rely on get_snapshot 
            # or implemented it inefficiently for now.
            # Let's try to use individual quote if possible, but AKShare is often bulk.
            
            # stock_zh_a_hist can give daily close, but not realtime tick.
            # Let's use get_snapshot logic here.
            snapshot = self.get_snapshot([code])
            if snapshot:
                return snapshot[0].get('price')
        except Exception as e:
            logger.error(f"AKShare get_price error: {e}")
        return None

    def get_snapshot(self, codes: List[str]) -> List[dict]:
        """
        Get snapshot for a list of codes.
        AKShare 'stock_zh_a_spot_em' returns all A-shares.
        """
        self._ensure_akshare()
        results = []
        try:
            # This function returns a large DF of all stocks. 
            # It's heavy but AKShare is designed this way for free data.
            df = ak.stock_zh_a_spot_em()
            
            # DF columns: 序号, 代码, 名称, 最新价, 涨跌幅, ...
            # Map standard columns
            
            # Filter for requested codes
            # Input codes might be "600000.SH" or "000001"
            # AKShare returns "600000" (pure digits)
            
            clean_codes = [c.split('.')[0] for c in codes]
            
            # Filter
            mask = df['代码'].isin(clean_codes)
            subset = df[mask]
            
            for _, row in subset.iterrows():
                try:
                    results.append({
                        "code": row['代码'],
                        "name": row['名称'],
                        "price": float(row['最新价']),
                        "change": float(row['涨跌幅']),
                        "open": float(row['今开']),
                        "high": float(row['最高']),
                        "low": float(row['最低']),
                        "vol": float(row['成交量'])
                    })
                except ValueError:
                    continue # Skip bad data
                    
            return results
            
        except Exception as e:
            logger.error(f"AKShare get_snapshot error: {e}")
            return []

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get daily history.
        code: "600519"
        start_date: "20230101"
        end_date: "20230131"
        """
        self._ensure_akshare()
        try:
            clean_code = code.split('.')[0]
            # AKShare uses YYYYMMDD
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")
            
            df = ak.stock_zh_a_hist(symbol=clean_code, start_date=start, end_date=end, adjust="qfq")
            
            # Rename columns to standard: date, open, high, low, close, volume
            # AKShare columns: 日期, 开盘, 收盘, 最高, 最低, 成交量, ...
            
            rename_map = {
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume"
            }
            df = df.rename(columns=rename_map)
            return df[list(rename_map.values())]
            
        except Exception as e:
            logger.error(f"AKShare get_history error: {e}")
            return pd.DataFrame()

    def sync_daily_data(self):
        """
        Synchronize daily snapshot from AKShare.
        """
        self._ensure_akshare()
        today = datetime.datetime.now().strftime("%Y%m%d")
        logger.info(f"Starting AKShare sync for {today}...")
        
        try:
            # Fetch spot data for all A-shares
            df = ak.stock_zh_a_spot_em()
            
            if df.empty:
                logger.warning(f"No data found from AKShare for {today}.")
                return

            # Ensure directory exists
            save_dir = os.path.join("data", "daily")
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            filename = os.path.join(save_dir, f"akshare_{today}.csv")
            df.to_csv(filename, index=False)
            logger.info(f"Successfully synced {len(df)} records from AKShare to {filename}")
            
        except Exception as e:
            logger.error(f"Error during AKShare sync: {e}")

    def get_table(self, table_name: str, date: str = None) -> pd.DataFrame:
        """
        Generic wrapper for other AKShare functions.
        table_name can be the function name in akshare.
        """
        self._ensure_akshare()
        try:
            if hasattr(ak, table_name):
                func = getattr(ak, table_name)
                # Try calling without args first, or with date if supported
                # This is a bit risky/generic, but allows flexibility.
                # For specific implementations, add valid cases.
                
                if date and 'date' in func.__code__.co_varnames:
                    return func(date=date)
                else:
                    return func()
            else:
                logger.warning(f"AKShare does not have function '{table_name}'")
        except Exception as e:
            logger.error(f"AKShare get_table '{table_name}' error: {e}")
        
        return pd.DataFrame()
