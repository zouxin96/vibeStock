from vibe_core.module import VibeModule
from vibe_core.event import Event
from vibe_data.factory import DataFactory
import time
import threading

class WatchlistModule(VibeModule):
    """
    Monitors a list of stocks using Sina Data Source (Realtime).
    Supports multiple independent instances via dynamic subscriptions.
    """
    
    def configure(self):
        self.running = True
        # Store subscriptions: { instance_id: { "codes": [...] } }
        self.subscriptions = {}
        self.subscriptions_lock = threading.Lock()
        
        try:
            self.adapter = DataFactory.create_provider({"data": {"provider": "sina"}})
        except Exception as e:
            print(f"[Watchlist] Failed to create Sina adapter: {e}")
            self.adapter = None

        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def get_ui_config(self):
        return {
            "id": "watchlist_main",
            "component": "watchlist-widget",
            "title": "Market Watchlist (Sina)",
            "default_col_span": "col-span-1 md:col-span-2 lg:col-span-1",
            "script_path": "widget.js",
            "config_default": {
                "codes": ["600519.SH", "000001.SZ", "600036.SH"]
            },
            "config_description": "Specify a list of stock codes to monitor. \nFormat: { \"codes\": [\"600519.SH\", \"000001.SZ\"] }"
        }

    def on_event(self, event: Event):
        pass
        
    def on_client_message(self, message: dict):
        """
        Handle messages from the frontend widget.
        Msg format: { "type": "subscribe", "widgetId": "...", "config": {...} }
        """
        msg_type = message.get("type")
        widget_id = message.get("widgetId")
        
        if msg_type == "subscribe" and widget_id:
            config = message.get("config", {})
            # Parse codes from config
            # Config might be { "codes": ["600519.SH", "000001.SZ"] }
            # Or comma separated string
            codes = config.get("codes", [])
            
            # Default if empty
            if not codes:
                codes = ["600519.SH", "000001.SZ", "600036.SH"]
            elif isinstance(codes, str):
                codes = [c.strip() for c in codes.split(',')]
                
            with self.subscriptions_lock:
                self.subscriptions[widget_id] = {"codes": codes}
                print(f"[Watchlist] Subscribed instance {widget_id} with {len(codes)} stocks.")
                
            # Trigger immediate update for this instance if possible (optional)

    def _update_loop(self):
        while self.running:
            if self.adapter:
                with self.subscriptions_lock:
                    # Snapshot of current subscriptions
                    subs = dict(self.subscriptions)
                
                # Batch all unique codes to optimize network? 
                # Or just loop per instance for simplicity?
                # Sina batch is efficient. Let's collect all unique codes first.
                all_codes = set()
                for sub in subs.values():
                    all_codes.update(sub["codes"])
                
                if all_codes:
                    try:
                        # Fetch all data once
                        data_list = self.adapter.get_snapshot(list(all_codes))
                        # Convert to dict for fast lookup: { code: data_row }
                        data_map = { row['code']: row for row in data_list }
                        
                        # Distribute to instances
                        for widget_id, sub in subs.items():
                            instance_data = []
                            for code in sub["codes"]:
                                # Sina adapter converts 600519.SH to sh600519
                                # We need to match whatever the adapter returns.
                                # The adapter returns 'code' as 'sh600519'.
                                # Our input was '600519.SH'.
                                # We need a helper to normalize keys or just search.
                                
                                # Quick fix: check normalized keys in map
                                # The adapter._convert_code logic is: 600519.SH -> sh600519
                                normalized = self.adapter._convert_code(code)
                                if normalized in data_map:
                                    instance_data.append(data_map[normalized])
                            
                            if instance_data:
                                if hasattr(self.context, 'broadcast_ui'):
                                    self.context.broadcast_ui(widget_id, instance_data)
                                    
                    except Exception as e:
                         print(f"[Watchlist] Update error: {e}")
            
            time.sleep(3)