from vibe_core.module import VibeModule
from vibe_core.event import Event
import datetime

class MarketDataRecorder(VibeModule):
    """
    Market Data Recorder Module.
    Fetches snapshot data periodically and saves it to CSV storage.
    """
    
    def configure(self):
        # Default recording interval: 1 minute
        self.trigger_on_cron("interval:60")
        
        # Watchlist to record (could be shared or config driven)
        self.watchlist = [
            "sh000001", "sz399006", "sh600519"
        ]

    def on_event(self, event: Event):
        # Only run on timer
        if event.type != "TIMER":
            return

        # Check if we can fetch data
        if hasattr(self.context.data, "get_snapshot"):
            data = self.context.data.get_snapshot(self.watchlist)
            
            if data:
                count = 0
                timestamp = datetime.datetime.now().isoformat()
                
                for item in data:
                    # Enrich with timestamp
                    item['timestamp'] = timestamp
                    # Save using storage service
                    # Category: market_snapshot
                    self.context.storage.save_record("market_snapshot", item)
                    count += 1
                
                self.context.logger.info(f"Recorded {count} market data snapshots.")
        else:
            self.context.logger.warning("Data provider does not support snapshots, cannot record.")
