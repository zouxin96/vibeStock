from vibe_core.module import VibeModule
from vibe_core.event import Event
from vibe_data.factory import DataFactory

class RealtimeMarketWatch(VibeModule):
    """
    真实行情监控模块
    从新浪财经获取实时数据，并推送到 Web 面板。
    """
    
    def __init__(self):
        super().__init__()
        self.description = "真实行情监控模块 - 从新浪财经获取实时数据，并推送到 Web 面板。"

    def configure(self):
        # 你的自选股列表
        default_watchlist = [
            "sh000001", # 上证指数
            "sz399006", # 创业板指
            "sh600519", # 贵州茅台
            "sz000858", # 五粮液
            "sz300750", # 宁德时代
            "sh601138", # 工业富联
            "sh601318", # 中国平安
            "sh600036", # 招商银行
            "sz002594", # 比亚迪
        ]
        
        self.watchlist = self.config.get("watchlist", default_watchlist)
        
        # 确保我们使用 Sina 源 (即使 config 没改，这里强行获取也可以，但最好走 ctx)
        # 这里演示如何每 3 秒刷新一次
        self.trigger_on_cron("interval:3")

    def on_event(self, event: Event):
        # 1. 强制转换 data provider 为 sina (如果尚未配置)
        # 为了演示方便，我们假设 ctx.data 已经是 SinaAdapter 或者我们直接用 provider 接口的扩展方法
        # 但标准做法是 ctx.data.get_snapshot
        
        # 检查 adapter 是否支持 snapshot
        if hasattr(self.context.data, "get_snapshot"):
            data = self.context.data.get_snapshot(self.watchlist)
            
            # 2. 推送到前端 "watchlist_main" 组件
            if data:
                self.context.output.dashboard("watchlist_main", data)
                #self.context.logger.info(f"Pushed {len(data)} realtime quotes.")
        else:
            self.context.logger.warning("Current data provider does not support 'get_snapshot'")
