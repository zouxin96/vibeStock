from vibe_core.module import VibeModule
from vibe_core.event import Event
import datetime
import os

class TushareSyncModule(VibeModule):
    """
    Tushare Data Synchronization Module.
    Ensures daily market data is synced after 16:00.
    Checks existence of data file; if missing, fetches immediately.
    """
    
    def __init__(self):
        super().__init__()
        self.description = "Tushare Data Synchronization Module. Ensures daily market data is synced after 16:00."

    def configure(self):
        # Check every minute
        self.trigger_on_cron("interval:60")
        self.attempted_sync_date = None

    def on_event(self, event: Event):
        # We only care about timer events
        if event.type != "TIMER":
            return

        now = datetime.datetime.now()
        
        # Only sync after market close (16:00)
        if now.hour >= 16:
            today_str_params = now.strftime("%Y%m%d") # Format for filename matches adapter
            today_str_display = now.strftime("%Y-%m-%d")
            
            # Check if we already attempted sync this session for today
            if self.attempted_sync_date == today_str_params:
                return

            # Check if data file exists
            # Note: Path must match TushareAdapter's save path
            file_path = os.path.join("data", "daily", f"daily_{today_str_params}.csv")
            
            if os.path.exists(file_path):
                # Data exists, no need to sync
                # We can mark it as attempted/done so we don't check file system every minute
                self.attempted_sync_date = today_str_params
                return

            self.context.logger.info(f"Data for {today_str_display} missing. triggering sync...")
            
            # Perform Sync
            self._do_sync()
            
            # Mark as attempted to prevent loops (e.g. on holidays when no data is returned)
            self.attempted_sync_date = today_str_params

    def _do_sync(self):
        if hasattr(self.context.data, "sync_daily_data"):
            self.context.data.sync_daily_data()
        else:
            # Fallback for when active provider isn't Tushare
            try:
                from vibe_core.data.adapter.stock_detail.tushare import TushareAdapter
                token = self.context.config.get("data", {}).get("tushare_token", "")
                adapter = TushareAdapter(token=token)
                adapter.sync_daily_data()
            except Exception as e:
                self.context.logger.error(f"Failed to run independent Tushare sync: {e}")
