import pandas as pd
import logging
import datetime
import os
from ..base import AKShareBase

try:
    import akshare as ak
except ImportError:
    ak = None

class AKShareMeta(AKShareBase):
    """
    负责元数据：板块概念、成分股、行业分类。
    """

    def get_ths_concepts(self) -> pd.DataFrame:
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()
        try:
            df = ak.stock_board_concept_name_ths()
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_ths_concepts 错误: {e}")
            return pd.DataFrame()

    def get_em_concepts(self) -> pd.DataFrame:
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()
        try:
            df = ak.stock_board_concept_name_em()
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_em_concepts 错误: {e}")
            return pd.DataFrame()

    def get_ths_sectors(self) -> pd.DataFrame:
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()
        try:
            df = ak.stock_board_industry_summary_ths()
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_ths_sectors 错误: {e}")
            return pd.DataFrame()

    def get_em_sectors(self) -> pd.DataFrame:
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()
        try:
            df = ak.stock_board_industry_name_em()
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_em_sectors 错误: {e}")
            return pd.DataFrame()

    def get_ths_concept_history(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()
        try:
            return ak.stock_board_concept_index_ths(symbol=symbol, start_date=start_date, end_date=end_date)
        except Exception as e:
            self.log(logging.ERROR, f"获取 {symbol} 历史数据错误: {e}")
            return pd.DataFrame()

    def get_concept_cons(self, symbol: str) -> pd.DataFrame:
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()
        try:
            return ak.stock_board_concept_cons_em(symbol=symbol)
        except Exception as e:
            self.log(logging.ERROR, f"获取概念 {symbol} 成分股失败: {e}")
            return pd.DataFrame()

    def get_industry_cons(self, symbol: str) -> pd.DataFrame:
        self._ensure_akshare()
        if ak is None: return pd.DataFrame()
        try:
            return ak.stock_board_industry_cons_em(symbol=symbol)
        except Exception as e:
            self.log(logging.ERROR, f"获取行业 {symbol} 成分股失败: {e}")
            return pd.DataFrame()

    def sync_concepts_and_sectors(self):
        self._ensure_akshare()
        if ak is None: return

        target_dir = os.path.join("data", "concepts")
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        tasks = [
            ("ths_concepts.csv", self.get_ths_concepts),
            ("em_concepts.csv", self.get_em_concepts),
            ("ths_sectors.csv", self.get_ths_sectors),
            ("em_sectors.csv", self.get_em_sectors),
        ]

        today = datetime.date.today()

        for filename, func in tasks:
            path = os.path.join(target_dir, filename)
            if os.path.exists(path):
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).date()
                if mtime == today:
                    self.log(logging.INFO, f"{filename} 已存在且为今日更新，跳过。" )
                    continue

            try:
                self.log(logging.INFO, f"正在获取 {filename}...")
                df = func()
                if not df.empty:
                    df.to_csv(path, index=False)
                else:
                    self.log(logging.WARNING, f"{filename} 结果为空")
            except Exception as e:
                self.log(logging.ERROR, f"同步 {filename} 失败: {e}")

    def sync_ths_concept_histories(self):
        """同步所有同花顺概念的历史数据。"""
        # Placeholder
        self.sync_concepts_and_sectors()
        self.log(logging.INFO, "Concept history sync logic placeholder.")

    def sync_board_constituent_data(self):
        """同步板块与成分股的对应关系"""
        self.log(logging.INFO, "Board constituent sync logic placeholder.")