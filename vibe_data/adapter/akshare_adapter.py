import pandas as pd
import logging
import datetime
import os
import json
import time
from typing import Optional, List
from ..provider import BaseFetcher, FetcherType, DataCategory, DataDimension

# 尝试导入 akshare，如果缺失则允许安全失败（不崩溃）
try:
    import akshare as ak
except ImportError:
    ak = None

class AKShareAdapter(BaseFetcher):
    """
    使用 AKShare (开源财经数据接口) 的数据提供者。
    Data Provider using AKShare (Open Source Financial Data).
    项目地址: https://github.com/akfamily/akshare
    """
    
    def __init__(self, **kwargs):
        super().__init__(FetcherType.POST_MARKET)
        if ak is None:
            self.log(logging.ERROR, "AKShare 未安装。请运行 `pip install akshare` 进行安装。" )
    
    def _ensure_akshare(self):
        """确保 AKShare 模块已加载，否则抛出异常。"""
        if ak is None:
            raise ImportError("未找到 AKShare 模块。请通过 pip 安装它。" )

    @property
    def data_dimension(self) -> DataDimension:
        """返回数据维度，这里是日期维度。"""
        return DataDimension.DATE

    @property
    def archive_filename_template(self) -> str:
        """定义存档文件名的模板。"""
        return "akshare_{date}.csv"

    def get_price(self, code: str, date: str = None) -> Optional[float]:
        """
        获取当前价格。
        AKShare 的实时接口通常返回一个 DataFrame。
        """
        self._ensure_akshare()
        try:
            # 使用 stock_zh_a_spot_em 获取实时数据
            # 这会返回所有股票的数据，所以如果只查询这一个，效率可能会比较低。
            # 理想情况下，我们应该缓存这个结果，或者如果有可用的更具体的函数则使用它。
            
            # 为了在这个特定方法中的效率，也许我们暂时只返回 None 并依赖 get_snapshot，
            # 或者暂时以低效的方式实现它。
            # 让我们尝试使用快照逻辑。
            snapshot = self.get_snapshot([code])
            if snapshot:
                return snapshot[0].get('price')
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_price 错误: {e}")
        return None

    def get_snapshot(self, codes: List[str]) -> List[dict]:
        """
        获取一组代码的快照数据。
        AKShare 'stock_zh_a_spot_em' 返回所有 A 股数据。
        """
        self._ensure_akshare()
        results = []
        try:
            # 此函数返回包含所有股票的大型 DataFrame。
            # 它比较重，但 AKShare 作为一个免费数据源是这样设计的。
            df = ak.stock_zh_a_spot_em()
            
            # DF 列名: 序号, 代码, 名称, 最新价, 涨跌幅, ...
            # 映射标准列
            
            # 过滤请求的代码
            # 输入代码可能是 "600000.SH" 或 "000001"
            # AKShare 返回 "600000" (纯数字)
            
            clean_codes = [c.split('.')[0] for c in codes]
            
            # 过滤
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
                    continue # 跳过错误数据
                    
            return results
            
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_snapshot 错误: {e}")
            return []

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日线历史数据。
        code: "600519"
        start_date: "20230101"
        end_date: "20230131"
        """
        self._ensure_akshare()
        try:
            clean_code = code.split('.')[0]
            # AKShare 使用 YYYYMMDD 格式
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")
            
            df = ak.stock_zh_a_hist(symbol=clean_code, start_date=start, end_date=end, adjust="qfq")
            
            # 重命名列为标准名称: date, open, high, low, close, volume
            # AKShare 列名: 日期, 开盘, 收盘, 最高, 最低, 成交量, ...
            
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
            self.log(logging.ERROR, f"AKShare get_history 错误: {e}")
            return pd.DataFrame()

    def sync_daily_data(self):
        """
        从 AKShare 同步每日快照数据。
        如果当日数据已存在，则跳过。
        """
        self._ensure_akshare()
        today = datetime.datetime.now().strftime("%Y%m%d")
        
        # 使用新的存储路径逻辑和文件名模板
        fname = self.get_archive_filename(date=today)
        filename = self.get_save_path(DataCategory.STOCK, fname)

        # 检查文件是否已存在
        if os.path.exists(filename):
            self.log(logging.INFO, f"{today} 的数据已存在于 {filename}，跳过同步。" )
            return

        self.log(logging.INFO, f"开始 AKShare 同步 {today}...")
        
        try:
            # 获取所有 A 股的实时数据
            df = ak.stock_zh_a_spot_em()
            
            if df.empty:
                self.log(logging.WARNING, f"AKShare 未返回 {today} 的数据。" )
                return
            
            df.to_csv(filename, index=False)
            self.log(logging.INFO, f"成功同步了 {len(df)} 条记录到 {filename}")
            
        except Exception as e:
            self.log(logging.ERROR, f"AKShare 同步期间出错: {e}")

    def get_table(self, table_name: str, date: str = None) -> pd.DataFrame:
        """
        其他 AKShare 函数的通用包装器。
        table_name 可以是 akshare 中的函数名。
        """
        self._ensure_akshare()
        try:
            if hasattr(ak, table_name):
                func = getattr(ak, table_name)
                # 首先尝试不带参数调用，或者如果支持则带日期调用
                # 这有点冒险/通用，但提供了灵活性。
                # 对于特定实现，请添加有效用例。
                
                if date and 'date' in func.__code__.co_varnames:
                    return func(date=date)
                else:
                    return func()
            else:
                self.log(logging.WARNING, f"AKShare 没有函数 '{table_name}'")
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_table '{table_name}' 错误: {e}")
        
        return pd.DataFrame()

    def get_ths_concepts(self) -> pd.DataFrame:
        """从同花顺获取概念板块列表。"""
        self._ensure_akshare()
        try:
            return ak.stock_board_concept_name_ths()
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_ths_concepts 错误: {e}")
            return pd.DataFrame()

    def get_em_concepts(self) -> pd.DataFrame:
        """从东方财富获取概念板块列表。"""
        self._ensure_akshare()
        try:
            return ak.stock_board_concept_name_em()
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_em_concepts 错误: {e}")
            return pd.DataFrame()

    def get_ths_sectors(self) -> pd.DataFrame:
        """从同花顺获取行业板块列表。"""
        self._ensure_akshare()
        try:
            return ak.stock_board_industry_summary_ths()
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_ths_sectors 错误: {e}")
            return pd.DataFrame()

    def get_em_sectors(self) -> pd.DataFrame:
        """从东方财富获取行业板块列表。"""
        self._ensure_akshare()
        try:
            return ak.stock_board_industry_name_em()
        except Exception as e:
            self.log(logging.ERROR, f"AKShare get_em_sectors 错误: {e}")
            return pd.DataFrame()

    def sync_concepts_and_sectors(self):
        """
        同步概念和行业数据到 'data/concepts/'。
        如果文件已存在且为今日更新，则跳过。
        """
        self._ensure_akshare()
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
            
            # 检查文件是否已存在且是今天修改的
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
                    self.log(logging.INFO, f"已保存 {filename} 到 {path}")
                else:
                    self.log(logging.WARNING, f"{filename} 结果为空")
            except Exception as e:
                self.log(logging.ERROR, f"同步 {filename} 失败: {e}")

    def get_ths_concept_history(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取特定同花顺概念的历史指数数据。"""
        self._ensure_akshare()
        try:
            return ak.stock_board_concept_index_ths(symbol=symbol, start_date=start_date, end_date=end_date)
        except Exception as e:
            self.log(logging.ERROR, f"获取 {symbol} 历史数据错误: {e}")
            return pd.DataFrame()

    def sync_ths_concept_histories(self):
        """
        同步所有同花顺概念的历史数据。
        基于现有文件进行增量同步。
        策略:
        1. 读取概念列表（如果缺失则获取）。
        2. 对于每个概念，检查本地历史文件。
        3. 如果存在，从 last_date + 1 开始获取。
        4. 如果缺失，从 20200101 开始获取。
        5. 如果数据已是最新的（next_date > now），则跳过。
        """
        self._ensure_akshare()
        
        # 1. 加载概念列表
        concepts_path = os.path.join("data", "concepts", "ths_concepts.csv")
        if not os.path.exists(concepts_path):
            self.log(logging.WARNING, "ths_concepts.csv 未找到。先运行 sync_concepts_and_sectors。" )
            self.sync_concepts_and_sectors()
            if not os.path.exists(concepts_path):
                return
        
        try:
            concepts_df = pd.read_csv(concepts_path)
        except Exception as e:
            self.log(logging.ERROR, f"读取概念文件失败: {e}")
            return

        # 2. 准备存储目录
        history_dir = os.path.join("data", "concepts", "history", "ths")
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)
            
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        
        # 3. 迭代
        name_col = '板块名称'
        if 'name' in concepts_df.columns:
            name_col = 'name'
        elif '板块名称' not in concepts_df.columns:
             self.log(logging.ERROR, "概念列表中未找到 '板块名称' 或 'name' 列。" )
             return
             
        symbols = concepts_df[name_col].unique()
        total = len(symbols)
        self.log(logging.INFO, f"开始同步 {total} 个同花顺概念的历史数据...")
        
        for i, symbol in enumerate(symbols):
            safe_name = str(symbol).replace("/", "_").replace("\\", "_").strip()
            if not safe_name: continue
            
            file_path = os.path.join(history_dir, f"{safe_name}.csv")
            start_date = "20200101" # 默认开始日期
            is_append = False
            
            # 检查现有文件
            if os.path.exists(file_path):
                try:
                    existing_df = pd.read_csv(file_path)
                    if not existing_df.empty and '日期' in existing_df.columns:
                        last_date_str = str(existing_df['日期'].max())
                        # 解析日期 (处理 YYYY-MM-DD 或 YYYYMMDD)
                        last_date = pd.to_datetime(last_date_str)
                        next_date = last_date + datetime.timedelta(days=1)
                        start_date = next_date.strftime("%Y%m%d")
                        
                        # 检查是否已经是最新
                        if next_date > datetime.datetime.now():
                            # 已经是最新了，跳过
                            continue
                        is_append = True
                except Exception as e:
                    self.log(logging.WARNING, f"读取 {symbol} 的现有文件错误，将重新获取所有: {e}")
                    is_append = False
            
            if start_date > today_str: continue
            
            self.log(logging.INFO, f"[{i+1}/{total}] 正在同步 {symbol}，从 {start_date} 开始...")
            
            df = self.get_ths_concept_history(symbol, start_date, today_str)
            
            if not df.empty:
                try:
                    if is_append:
                        df.to_csv(file_path, mode='a', header=False, index=False)
                    else:
                        df.to_csv(file_path, index=False)
                except Exception as e:
                    self.log(logging.ERROR, f"保存 {symbol} 失败: {e}")
            else:
                 self.log(logging.DEBUG, f"{symbol} 没有新数据")
                 
        self.log(logging.INFO, "同花顺概念历史数据同步完成。" )

    def get_concept_cons(self, symbol: str) -> pd.DataFrame:
        """获取概念板块成分股"""
        self._ensure_akshare()
        try:
            return ak.stock_board_concept_cons_em(symbol=symbol)
        except Exception as e:
            self.log(logging.ERROR, f"获取概念 {symbol} 成分股失败: {e}")
            return pd.DataFrame()

    def get_industry_cons(self, symbol: str) -> pd.DataFrame:
        """获取行业板块成分股"""
        self._ensure_akshare()
        try:
            return ak.stock_board_industry_cons_em(symbol=symbol)
        except Exception as e:
            self.log(logging.ERROR, f"获取行业 {symbol} 成分股失败: {e}")
            return pd.DataFrame()

    def sync_board_constituent_data(self):
        """
        同步板块（概念+行业）与成分股的对应关系，并生成双向字典。
        保存为:
        - data/concepts/board_stocks_map.json
        - data/concepts/stock_boards_map.json
        """
        self._ensure_akshare()
        
        # 1. 获取所有板块列表
        self.log(logging.INFO, "正在获取概念板块列表...")
        concepts_df = self.get_em_concepts()
        self.log(logging.INFO, "正在获取行业板块列表...")
        sectors_df = self.get_em_sectors()
        
        board_stocks = {} # { "board_name": ["stock_code", ...] }
        stock_boards = {} # { "stock_code": ["board_name", ...] }
        
        # 辅助函数来处理列表
        def process_boards(df, is_industry=False):
            if df.empty: return
            
            # 检查列名，AKShare 返回通常是 '板块名称'
            if '板块名称' not in df.columns:
                self.log(logging.ERROR, "板块列表缺少 '板块名称' 列")
                return

            names = df['板块名称'].tolist()
            total = len(names)
            type_str = "行业" if is_industry else "概念"
            
            self.log(logging.INFO, f"开始处理 {total} 个{type_str}板块...")
            
            for i, name in enumerate(names):
                if i % 10 == 0:
                    self.log(logging.INFO, f"[{i+1}/{total}] 正在获取 {type_str}: {name}")
                
                try:
                    if is_industry:
                        cons_df = self.get_industry_cons(name)
                    else:
                        cons_df = self.get_concept_cons(name)
                        
                    if not cons_df.empty and '代码' in cons_df.columns:
                        codes = cons_df['代码'].tolist()
                        # 确保代码是字符串
                        codes = [str(c) for c in codes]
                        board_stocks[name] = codes
                        
                        for code in codes:
                            if code not in stock_boards:
                                stock_boards[code] = []
                            if name not in stock_boards[code]:
                                stock_boards[code].append(name)
                    
                    # 避免请求过快，轻微延迟
                    time.sleep(0.5) 
                    
                except Exception as e:
                    self.log(logging.ERROR, f"处理板块 {name} 出错: {e}")

        process_boards(concepts_df, is_industry=False)
        process_boards(sectors_df, is_industry=True)
        
        # 保存
        save_dir = os.path.join("data", "concepts")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        bs_path = os.path.join(save_dir, "board_stocks_map.json")
        sb_path = os.path.join(save_dir, "stock_boards_map.json")
        
        try:
            with open(bs_path, 'w', encoding='utf-8') as f:
                json.dump(board_stocks, f, ensure_ascii=False, indent=2)
            
            with open(sb_path, 'w', encoding='utf-8') as f:
                json.dump(stock_boards, f, ensure_ascii=False, indent=2)
                
            self.log(logging.INFO, f"板块成分股映射已保存:\n{bs_path}\n{sb_path}")
            
        except Exception as e:
            self.log(logging.ERROR, f"保存映射文件失败: {e}")
