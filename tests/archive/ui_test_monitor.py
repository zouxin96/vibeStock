from vibe_core.module import VibeModule
from vibe_core.event import Event
import random
import time

class DashboardTestMonitor(VibeModule):
    """
    Simulates a watchlist monitor for the Dashboard UI.
    Pushes updates every 3 seconds.
    """
    
    def configure(self):
        # Register a cron job every 3 seconds
        self.trigger_on_cron("interval:3")
        
        # Base data
        self.stocks = [
            {"code": "000001.SZ", "name": "PingAn Bank", "base": 12.50},
            {"code": "600519.SH", "name": "Moutai", "base": 1800.00},
            {"code": "300750.SZ", "name": "CATL", "base": 230.00},
            {"code": "00700.HK", "name": "Tencent", "base": 350.00},
            {"code": "AAPL.US", "name": "Apple", "base": 175.00},
        ]

    def on_event(self, event: Event):
        # Generate random fluctuations
        data = []
        for stock in self.stocks:
            change_pct = round(random.uniform(-2.0, 2.0), 2)
            current_price = stock["base"] * (1 + change_pct / 100)
            
            data.append({
                "code": stock["code"],
                "name": stock["name"],
                "price": current_price,
                "change": change_pct
            })
            
        # Push to Dashboard
        # Widget ID must match what's in index.html
        self.context.output.dashboard("watchlist_main", data)
