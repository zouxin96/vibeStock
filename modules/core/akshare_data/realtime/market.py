import pandas as pd
import logging
from typing import Optional, List
from base import AKShareBase

try:
    import akshare as ak
except ImportError:
    ak = None

class AKShareMarket(AKShareBase):
    """
    负责行情数据：实时价格、历史K线、快照。
    """
    
    def get_price(self, code: str, date: str = None) -> Optional[float]:
        self._ensure_akshare()
        if ak is None: return None

        try:
            snapshot = self.get_snapshot([code])
            if snapshot:
                return snapshot[0].get('price')
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_price 错误: {e}")
        return None

    def get_full_snapshot(self) -> pd.DataFrame:
        """
        获取全市场实时行情数据 (Raw DataFrame)。
        用于中间层缓存。
        """
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()

        try:
            df = ak.stock_zh_a_spot_em()
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_full_snapshot 错误: {e}")
            return pd.DataFrame()

    def get_snapshot(self, codes: List[str]) -> List[dict]:
        """
        获取一组代码的快照数据。
        """
        results = []
        try:
            # 优先使用全量获取逻辑（配合 Aggregator）
            df = self.get_full_snapshot()
            
            if df is None or df.empty:
                return []
            
            clean_codes = [c.split('.')[0] for c in codes]
            
            # 检查列名是否存在
            if '代码' not in df.columns:
                 self.log(logging.WARNING, "get_full_snapshot 返回数据缺少 '代码' 列")
                 return []

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
                    continue 
                    
            return results
            
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_snapshot 错误: {e}")
            return []

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()

        try:
            clean_code = code.split('.')[0]
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")
            
            df = ak.stock_zh_a_hist(symbol=clean_code, start_date=start, end_date=end, adjust="qfq")
            
            rename_map = {
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume"
            }
            df = df.rename(columns=rename_map)
            # 容错：只选择存在的列
            cols = [c for c in list(rename_map.values()) if c in df.columns]
            return df[cols]
            
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_history 错误: {e}")
            return pd.DataFrame()