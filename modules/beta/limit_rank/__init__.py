from vibe_core.module import VibeModule
from vibe_core.event import Event
import logging
import pandas as pd
import time

class LimitOrderRankModule(VibeModule):
    """
    涨停封单排序模块
    定期获取涨停股池，并按封板资金降序排列。
    """
    dependencies = ['AkShareDataModule']
    
    def __init__(self, context=None):
        # 基类 VibeModule.__init__ 不接受参数
        super().__init__()
        # 如果 server.py 实例化时传入了 context，提前保存
        if context:
            self.context = context
        self.id = "limit_rank"
        self.name = "Limit Order Rank"
        self.interval = 10  # 更新间隔(秒)
        
        # Logging stats
        self.last_log_time = time.time()
        self.call_count = 0
        self.first_run = True

    def configure(self):
        """
        由 initialize(context) 自动调用。
        """
        # print(f"DEBUG: LimitOrderRankModule CONFIGURE called! Context data: {type(self.context.data)}")
        self.context.logger.info(f"{self.name} started. Refresh interval: {self.interval}s")
        
        # 立即运行一次
        self.process()
        
        # 注册定时任务 (放在 process 之后，确保第一次已经执行)
        self.context.register_cron(self, f"interval:{self.interval}")


    def on_stop(self):
        self.context.logger.info(f"{self.name} stopped.")

    def on_event(self, event: Event):
        if event.type == "TIMER":
            self.process()

    def process(self):
        """
        获取数据并排序
        """
        # DEBUG LOG
        # with open("debug_limit_rank.log", "a") as f: f.write(f"{time.time()}: Process started\n")

        if self.context.data is None:
            # with open("debug_limit_rank.log", "a") as f: f.write("Context Data is None\n")
            return

        try:
            # 直接尝试获取数据 (HybridProvider 会自动路由)
            # 注意: 第一次调用可能会触发 AKShareAdapter 的初始化日志
            if not hasattr(self.context.data, 'get_limit_up_pool'):
                 if self.first_run:
                     self.context.logger.warning("Data provider does not support `get_limit_up_pool`")
                 return

            df = self.context.data.get_limit_up_pool()
            
            # with open("debug_limit_rank.log", "a") as f: f.write(f"Got DF: {type(df)}\n")

            if df is None:
                self.context.logger.error("get_limit_up_pool returned None (Should be DataFrame)")
                return

            if df.empty:

                # 只有第一次或每分钟 Log 一次空数据警告，避免刷屏
                if self.first_run or (time.time() - self.last_log_time >= 60):
                     self.context.logger.info("当前无涨停股数据 (或是非交易时间/数据源空)。")
                return

            # 检查关键列
            target_col = '封板资金'
            if target_col not in df.columns:
                self.context.logger.warning(f"数据中缺少 '{target_col}' 列，无法排序。可用列: {df.columns.tolist()}")
                return

            # 确保是数值类型
            df[target_col] = pd.to_numeric(df[target_col], errors='coerce').fillna(0)

            # 排序: 封板资金降序
            sorted_df = df.sort_values(by=target_col, ascending=False)

            # 选取 Top 列表 (例如前 50)
            top_list = sorted_df.head(50)
            
            # 构建输出数据
            display_cols = ['代码', '名称', '最新价', '涨跌幅', '封板资金', '连板数', '所属行业']
            # 过滤存在的列
            cols = [c for c in display_cols if c in top_list.columns]
            
            result_df = top_list[cols]
            
            # 1. 统计与日志聚合
            self.call_count += 1
            now = time.time()
            if self.first_run:
                self.context.logger.info(f"First run processed {len(result_df)} limit rank stocks.")
                self.first_run = False
                self.last_log_time = now
            elif now - self.last_log_time >= 60:
                self.context.logger.info(f"[LimitRank Activity 60s] Processed: {self.call_count} calls. Last batch: {len(result_df)} stocks.")
                self.last_log_time = now
                self.call_count = 0

            # 2. 推送到前端
            payload = result_df.to_dict(orient='records')
            self.context.broadcast_ui("limit_rank", payload)
            
        except AttributeError as e:
            self.context.logger.error(f"Current DataProvider does not support `get_limit_up_pool`: {e}")
        except Exception as e:
            self.context.logger.error(f"处理涨停排序时出错: {e}")

    @classmethod
    def get_ui_config(cls):
        """
        返回前端 Widget 配置 (静态配置，无需实例)
        """
        return {
            "id": "limit_rank",
            "title": "Limit Up Rank (Funds)",
            "component": "limit-rank-widget",
            "default_col_span": "col-span-1",
            "config_default": {},
            "config_description": "Displays the top limit-up stocks sorted by blocking funds.",
            "script_path": "widget.js" 
        }