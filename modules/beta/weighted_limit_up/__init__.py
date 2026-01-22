from vibe_core.module import VibeModule
from vibe_core.event import Event
import logging
import pandas as pd
import time

class WeightedLimitUpModule(VibeModule):
    """
    加权连板排序模块
    定期获取涨停股池，并按 加权连板数 (连板数 * 涨跌幅) 降序排列。
    """
    dependencies = ['AkShareDataModule']
    
    def __init__(self, context=None):
        super().__init__()
        if context:
            self.context = context
        self.id = "weighted_limit_up"
        self.name = "Weighted Limit Up Rank"
        self.interval = 10  # 更新间隔(秒)
        
        self.last_log_time = time.time()
        self.call_count = 0
        self.first_run = True

    def configure(self):
        self.context.logger.info(f"{self.name} started. Refresh interval: {self.interval}s")
        self.process()
        self.context.register_cron(self, f"interval:{self.interval}")

    def on_stop(self):
        self.context.logger.info(f"{self.name} stopped.")

    def on_event(self, event: Event):
        if event.type == "TIMER":
            self.process()

    def process(self):
        if self.context.data is None:
            return

        try:
            if not hasattr(self.context.data, 'get_limit_up_pool'):
                 if self.first_run:
                     self.context.logger.warning("Data provider does not support `get_limit_up_pool`")
                 return

            df = self.context.data.get_limit_up_pool()
            
            if df is None:
                self.context.logger.error("get_limit_up_pool returned None")
                return

            if df.empty:
                if self.first_run or (time.time() - self.last_log_time >= 60):
                     self.context.logger.info("当前无涨停股数据。")
                return

            # 检查关键列
            req_cols = ['连板数', '涨跌幅']
            if not all(c in df.columns for c in req_cols):
                self.context.logger.warning(f"数据缺少必要列 {req_cols}，可用: {df.columns.tolist()}")
                return

            # 类型转换
            for c in req_cols:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

            # 计算权重: 连板数 * 涨跌幅
            # 创业板/科创板涨跌幅约为20，主板约为10，乘法自动体现权重
            df['weight'] = df['连板数'] * df['涨跌幅']

            # 排序: 权重降序
            sorted_df = df.sort_values(by='weight', ascending=False)

            top_list = sorted_df.head(50)
            
            display_cols = ['代码', '名称', '最新价', '涨跌幅', '连板数', 'weight', '所属行业']
            cols = [c for c in display_cols if c in top_list.columns]
            
            result_df = top_list[cols]
            
            # 日志
            self.call_count += 1
            now = time.time()
            if self.first_run:
                self.context.logger.info(f"First run processed {len(result_df)} weighted limit stocks.")
                self.first_run = False
                self.last_log_time = now
            elif now - self.last_log_time >= 60:
                self.context.logger.info(f"[WeightedLimitUp Activity 60s] Processed: {self.call_count} calls.")
                self.last_log_time = now
                self.call_count = 0

            # 推送
            payload = result_df.to_dict(orient='records')
            self.context.broadcast_ui("weighted_limit_up", payload)
            
        except Exception as e:
            self.context.logger.error(f"处理加权连板排序时出错: {e}")

    @classmethod
    def get_ui_config(cls):
        return {
            "id": "weighted_limit_up",
            "title": "Weighted Limit Up Rank",
            "component": "weighted-limit-up-widget",
            "default_col_span": "col-span-1",
            "config_default": {},
            "config_description": "Displays limit-up stocks sorted by Weighted Days (Days * Increase%).",
            "script_path": "widget.js" 
        }
