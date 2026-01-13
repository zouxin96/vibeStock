from vibe_core.module import VibeModule
from vibe_core.event import Event
from vibe_data.factory import DataFactory
import datetime
import os

class InfoSyncModule(VibeModule):
    """
    Information Data Synchronization Module.
    Fetches concepts, industries, and other meta-data.
    """
    
    def __init__(self):
        super().__init__()
        self.description = "Info Sync Module - Fetches Concept/Sector data from Tushare."
        self.adapter = None

    def configure(self):
        # Sync once a day, check every hour
        self.trigger_on_cron("interval:3600")
        self.last_sync_date = None
        
    def initialize(self, context):
        super().initialize(context)
        # Initialize the specific adapter manually or via factory
        # We use factory to get the class, but we need to instantiate it separate from context.data 
        # (which is the main market data provider)
        # Or we can just instantiate it here if we know the token.
        
        try:
            # Re-use config from context
            self.adapter = DataFactory.create_provider({
                "data": {
                    "provider": "tushare_info",
                    "tushare_token": self.context.config.get("data", {}).get("tushare_token", "")
                }
            })
            self.context.logger.info("InfoSyncModule initialized with TushareInfoAdapter.")
        except Exception as e:
            self.context.logger.error(f"Failed to init Info Adapter: {e}")

    def on_event(self, event: Event):
        if event.type != "TIMER":
            return

        today = datetime.datetime.now().strftime("%Y%m%d")
        
        if self.last_sync_date == today:
            return
            
        # Run sync
        self.context.logger.info("Starting Info Data Sync...")
        self._sync()
        self.last_sync_date = today

    def _sync(self):
        if not self.adapter:
            return

        # Sync THS Concepts (List only, members require separate on-demand fetch to save quota)
        self.adapter.sync_all_concepts(src="ths")
        
        # Sync SW Industries (Shenwan)
        try:
            df = self.adapter.get_industry_list(src="SW2021", level="L1")
            if not df.empty:
                path = self.adapter.get_save_path(self.adapter.fetcher_type.POST_MARKET.value, f"industry_sw2021_{datetime.date.today()}.csv") 
                # Wait, fetcher_type is enum. adapter.get_save_path takes DataCategory
                # Let's use the adapter's method directly if possible or the helper
                
                # Using helper correctly:
                from vibe_data.provider import DataCategory
                path = self.adapter.get_save_path(DataCategory.INFO, f"industry_sw2021_{datetime.date.today()}.csv")
                
                df.to_csv(path, index=False)
                self.context.logger.info(f"Saved SW2021 industries to {path}")
        except Exception as e:
            self.context.logger.error(f"Error syncing industries: {e}")
