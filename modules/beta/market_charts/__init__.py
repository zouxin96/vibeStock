from vibe_core.module import VibeModule
from vibe_core.event import Event
import threading
import time
import random
import datetime

class MarketChartsModule(VibeModule):
    """
    Provides demo charts: Sector Distribution (Pie), Market Trend (Line), and Stock K-Line (Candle).
    """
    
    def configure(self):
        self.running = True
        self.thread = threading.Thread(target=self._data_loop, daemon=True)
        self.thread.start()

    def get_ui_config(self):
        return [
            {
                "id": "sector_pie",
                "component": "sector-pie-widget",
                "title": "Sector Distribution",
                "default_col_span": "col-span-1",
                "script_path": "widget.js",
                "config_default": {},
                "config_description": "No configuration available for this demo widget."
            },
            {
                "id": "index_line",
                "component": "index-line-widget",
                "title": "Index Trend (Live)",
                "default_col_span": "col-span-1 md:col-span-2",
                "script_path": "widget.js",
                "config_default": {},
                "config_description": "No configuration available for this demo widget."
            },
            {
                "id": "stock_kline",
                "component": "stock-kline-widget",
                "title": "Moutai (600519) Day K",
                "default_col_span": "col-span-1 md:col-span-2",
                "script_path": "widget.js",
                "config_default": {},
                "config_description": "No configuration available for this demo widget."
            }
        ]

    def on_event(self, event: Event):
        pass

    def _data_loop(self):
        # Initial Data Generation
        sectors = [
            {"name": "Tech", "value": 30},
            {"name": "Finance", "value": 25},
            {"name": "Consumer", "value": 20},
            {"name": "Energy", "value": 15},
            {"name": "Healthcare", "value": 10}
        ]
        
        # Line Chart Buffer
        trend_data = []
        base_price = 3000
        
        while self.running:
            # 1. Update Pie
            # Randomly shift values
            for s in sectors:
                s["value"] += random.randint(-2, 2)
                if s["value"] < 5: s["value"] = 5
            
            # 2. Update Line (Append new point)
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            change = random.uniform(-5, 5)
            base_price += change
            trend_data.append({"time": now_str, "value": round(base_price, 2)})
            if len(trend_data) > 50: trend_data.pop(0)
            
            # 3. K-Line Data (Simulated Daily)
            # Generate 30 days of random K-line data
            kline_data = self._generate_kline(30)

            # Broadcast
            if hasattr(self.context, 'broadcast_ui'):
                self.context.broadcast_ui("sector_pie", sectors)
                self.context.broadcast_ui("index_line", trend_data)
                # K-Line usually doesn't update every second, but for demo we push it.
                # To save bandwidth, maybe send only if changed. Here we send always.
                self.context.broadcast_ui("stock_kline", kline_data)

            time.sleep(2)

    def _generate_kline(self, count):
        data = []
        price = 1000
        start_date = datetime.date.today() - datetime.timedelta(days=count)
        
        for i in range(count):
            date_str = (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            open_p = price + random.uniform(-10, 10)
            close_p = open_p + random.uniform(-20, 20)
            low_p = min(open_p, close_p) - random.uniform(0, 10)
            high_p = max(open_p, close_p) + random.uniform(0, 10)
            
            data.append({
                "date": date_str,
                "open": round(open_p, 2),
                "close": round(close_p, 2),
                "low": round(low_p, 2),
                "high": round(high_p, 2)
            })
            price = close_p
        return data
