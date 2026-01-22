from vibe_core.module import VibeModule
from vibe_core.event import Event
import datetime
import traceback

try:
    import akshare as ak
    import pandas as pd
except ImportError:
    ak = None
    pd = None

class LimitUpMonitor(VibeModule):
    """
    涨停数据监控服务模块
    功能：每天 09:20 - 15:30 每分钟抓取一次涨停数据并存档
    """
    dependencies = ["AkShareDataModule"]

    def __init__(self, context=None):
        super().__init__()
        if context:
            self.context = context

    def configure(self):
        self.name = "涨停监控服务"
        self.category = "Service"
        self._trade_dates_cache = None
        self._last_cache_date = None
        
        # 注册每 10 秒运行一次 (UI更新更及时，底层已有缓存和IO限流)
        self.context.register_cron(self, "interval:10")
        self.context.logger.info(f"[{self.name}] 已启动: 计划每日 09:20-15:30 运行")

    def on_event(self, event: Event):
        if event.type == "TIMER":
            self.check_and_run()

    def is_trading_day(self, current_date):
        """检查指定日期是否为交易日"""
        if current_date.weekday() >= 5: 
            return False, "Weekend"

        if ak is None:
            return True, "AKShare Missing"

        date_str = current_date.strftime("%Y-%m-%d")
        
        if self._trade_dates_cache is not None and self._last_cache_date == date_str:
            pass 
        else:
            try:
                self.context.logger.info(f"[{self.name}] Syncing trade calendar...")
                df = ak.tool_trade_date_hist_sina()
                if df is not None and not df.empty:
                    dates = pd.to_datetime(df['trade_date'])
                    trade_dates = set(d.strftime("%Y-%m-%d") for d in dates)
                    self._trade_dates_cache = trade_dates
                    self._last_cache_date = date_str
                else:
                    return True, "Calendar Empty"
            except Exception as e:
                return True, f"Error: {e}"

        if self._trade_dates_cache and date_str in self._trade_dates_cache:
            return True, "Trading Day"
        else:
            return False, "Holiday"

    def check_and_run(self):
        now = datetime.datetime.now()
        if now.weekday() >= 5: return

        # 定义时间窗口
        start_time = now.replace(hour=9, minute=20, second=0, microsecond=0)
        end_time = now.replace(hour=15, minute=30, second=0, microsecond=0)

        if not (start_time <= now <= end_time):
            return

        is_trading, reason = self.is_trading_day(now)
        if not is_trading:
            return

        self._run_task(now)

    def _run_task(self, now):
        try:
            # self.context.logger.info(f"[{self.name}] Fetching limit up data...")
            if not hasattr(self.context.data, 'get_limit_up_pool'):
                return
            df = self.context.data.get_limit_up_pool()
            if df is not None and not df.empty:
                count = len(df)
                
                # Sort for top stocks
                top_stocks = []
                if '连板数' in df.columns:
                     df['连板数'] = pd.to_numeric(df['连板数'], errors='coerce').fillna(0)
                     sorted_df = df.sort_values(by='连板数', ascending=False)
                     top_5 = sorted_df.head(5)
                     # Select only necessary fields
                     cols = ['名称', '连板数', '代码']
                     cols = [c for c in cols if c in top_5.columns]
                     top_stocks = top_5[cols].to_dict(orient='records')

                # Only log every minute or so to avoid spamming since we run every 10s now
                # Or just log debug.
                # self.context.logger.info(f"[{self.name}] Success: {count} records")
                
                monitor_data = {
                    "last_run": now.strftime("%H:%M:%S"),
                    "count": count,
                    "status": "Running",
                    "top_stocks": top_stocks
                }
                self.context.broadcast_ui("limit_up_monitor", monitor_data)
        except Exception as e:
            self.context.logger.error(f"[{self.name}] Task Error: {e}")

    def get_ui_config(self):
        return {
            "id": "limit_up_monitor",
            "name": "涨停监控服务",
            "component": "LimitUpMonitorWidget",
            "default_layout": {"w": 4, "h": 4}
        }