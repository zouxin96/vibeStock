from vibe_core.module import VibeModule
from vibe_core.event import Event
import pandas as pd
import time

class MarketHeatmapModule(VibeModule):
    """
    市场行业热力图模块
    展示各行业的实时涨跌分布。
    """
    
    def __init__(self, context=None):
        super().__init__()
        if context:
            self.context = context
        self.id = "market_heatmap"
        self.name = "Market Heatmap"
        self.interval = 10  # 提高刷新频率，与 Limit Rank 保持一致
        
        self.last_log_time = 0

    def configure(self):
        """模块初始化"""
        self.context.logger.info(f"{self.name} module loaded.")
        
        # 立即运行一次
        self.process()
        
        # 注册定时任务
        self.context.register_cron(self, f"interval:{self.interval}")

    def on_event(self, event: Event):
        if event.type == "TIMER":
            self.process()

    def process(self):
        """获取数据并推送到前端"""
        t0 = time.time()
        
        if self.context.data is None:
            return

        try:
            # 1. 获取行业板块数据
            if not hasattr(self.context.data, 'get_em_sectors'):
                 return

            t1 = time.time()
            df_sectors = self.context.data.get_em_sectors()
            t2 = time.time()
            if df_sectors is None or df_sectors.empty:
                self.context.logger.warning(f"Heatmap: get_em_sectors empty. Cost: {t2-t1:.2f}s")
                return

            # 2. 获取涨停股数据用于计算权重
            df_limit = self.context.data.get_limit_up_pool()
            t3 = time.time()
            
            # self.context.logger.info(f"Heatmap Data Fetch: Sectors={t2-t1:.2f}s, LimitPool={t3-t2:.2f}s")

            sector_weights = {} # { '行业名': weighted_count }

            if not df_limit.empty:
                # 确保列名正确
                if '所属行业' in df_limit.columns and '涨跌幅' in df_limit.columns:
                    # 转换数值
                    df_limit['涨跌幅'] = pd.to_numeric(df_limit['涨跌幅'], errors='coerce').fillna(0)
                    
                    # 遍历计算权重
                    for _, row in df_limit.iterrows():
                        industry = row['所属行业']
                        if not industry: continue
                        
                        # 规则: 涨幅 > 11% (20cm) 记 2 分，否则 1 分
                        weight = 2 if row['涨跌幅'] > 11 else 1
                        
                        sector_weights[industry] = sector_weights.get(industry, 0) + weight

            # 3. 数据合并与清洗
            if '涨跌幅' in df_sectors.columns:
                df_sectors['涨跌幅'] = pd.to_numeric(df_sectors['涨跌幅'], errors='coerce').fillna(0)
                # 排序：仍然按行业涨跌幅降序
                df_sectors = df_sectors.sort_values(by='涨跌幅', ascending=False)
            
            # 取前 30 个板块
            top_df = df_sectors.head(30).copy()
            
            # 映射权重
            # 注意: df_sectors['板块名称'] 是行业名
            top_df['limit_weight'] = top_df['板块名称'].map(lambda x: sector_weights.get(x, 0))
            
            # 转换列名
            rename_map = {
                '板块名称': 'name',
                '最新价': 'price',
                '涨跌幅': 'change',
                '总市值': 'market_cap'
            }
            # 保留需要的列
            final_df = top_df.rename(columns=rename_map)
            payload_cols = ['name', 'price', 'change', 'market_cap', 'limit_weight']
            # 容错: 确保列存在
            payload_cols = [c for c in payload_cols if c in final_df.columns]
            
            payload = final_df[payload_cols].to_dict(orient='records')
            
            # 每分钟记录一次日志
            now = time.time()
            if now - self.last_log_time >= 60:
                self.context.logger.info(f"[Heatmap] Broadcasted {len(payload)} sectors. Cost: {now-t0:.2f}s")
                self.last_log_time = now
                
            # 推送 UI 数据
            self.context.broadcast_ui("widget_market_heatmap", payload)
            
        except Exception as e:
            self.context.logger.error(f"Heatmap process error: {e}")

    @classmethod
    def get_ui_config(cls):
        """返回前端配置"""
        return {
            "id": "market_heatmap",
            "title": "Industry Heatmap (Weighted Limit Up)",
            "component": "market-heatmap-widget",
            "default_col_span": "col-span-1 md:col-span-2",
            "config_default": {},
            "config_description": "Displays top industries sorted by change. Box size represents weighted limit-up count (20cm=2, 10cm=1).",
            "script_path": "widget.js" 
        }
