from vibe_core.module import VibeModule
from vibe_core.event import Event
import random
import datetime

class DashboardTestChart(VibeModule):
    """
    Simulates K-Line data for the Dashboard UI.
    Pushes data once on startup (simulated via 5s delay).
    """
    
    def configure(self):
        # Trigger once shortly after startup
        self.trigger_on_cron("interval:5")
        self.has_sent = False

    def on_event(self, event: Event):
        if self.has_sent:
            return
            
        # Generate 30 days of mock K-Line data
        dates = []
        values = []
        
        price = 3000.0
        start_date = datetime.date.today() - datetime.timedelta(days=45)
        
        for i in range(30):
            date_str = (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            
            open_p = price + random.uniform(-20, 20)
            close_p = open_p + random.uniform(-30, 30)
            low_p = min(open_p, close_p) - random.uniform(0, 10)
            high_p = max(open_p, close_p) + random.uniform(0, 10)
            
            dates.append(date_str)
            values.append([open_p, close_p, low_p, high_p])
            
            price = close_p
            
        payload = {
            "dates": dates,
            "values": values
        }
        
        self.context.output.dashboard("chart_sh000001", payload)
        self.has_sent = True
