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
            codes = config.get("codes", [])
            
            # Default if empty
            if not codes:
                codes = ["600519.SH", "000001.SZ", "600036.SH"]
            elif isinstance(codes, str):
                codes = [c.strip() for c in codes.split(',')]
                
            with self.subscriptions_lock:
                self.subscriptions[widget_id] = {"codes": codes}
                print(f"[Watchlist] Subscribed instance {widget_id} with {len(codes)} stocks: {codes}")

    def _update_loop(self):
        while self.running:
            if self.adapter:
                with self.subscriptions_lock:
                    # Snapshot of current subscriptions
                    subs = dict(self.subscriptions)
                
                if not subs:
                    time.sleep(1)
                    continue

                all_codes = set()
                for sub in subs.values():
                    all_codes.update(sub["codes"])
                
                if all_codes:
                    try:
                        # Fetch all data once
                        data_list = self.adapter.get_snapshot(list(all_codes))
                        
                        # Data Mapping: Sina adapter returns codes in lowercase/different format sometimes
                        # We need to map back to the requested codes.
                        # Strategy: Create a map of normalized_code -> data_row
                        # And a map of requested_code -> normalized_code
                        
                        # 1. Normalize data keys
                        # Sina adapter output 'code' is usually 'sh600519'
                        data_map = { row['code']: row for row in data_list }
                        
                        # 2. Distribute to instances
                        for widget_id, sub in subs.items():
                            instance_data = []
                            for req_code in sub["codes"]:
                                # Convert requested '600519.SH' to 'sh600519' using adapter's helper if available
                                # Or manually matching logic. 
                                # adapter._convert_code is what we want.
                                if hasattr(self.adapter, '_convert_code'):
                                    norm_code = self.adapter._convert_code(req_code)
                                else:
                                    # Fallback simple converter
                                    if '.' in req_code:
                                        num, suffix = req_code.split('.')
                                        norm_code = f"{suffix.lower()}{num}"
                                    else:
                                        norm_code = req_code.lower()
                                
                                if norm_code in data_map:
                                    # Inject the original requested code for display consistency if needed
                                    # But widget expects 'code', 'name', 'price', etc.
                                    # Let's keep the row as is, or override 'code' to match display preference?
                                    # The widget displays row.code. Sina returns 'sh600519'. User might prefer '600519.SH'.
                                    # Let's override it back for display.
                                    row = data_map[norm_code].copy()
                                    row['code'] = req_code
                                    instance_data.append(row)
                            
                            if instance_data:
                                if hasattr(self.context, 'broadcast_ui'):
                                    self.context.broadcast_ui(widget_id, instance_data)
                                    
                    except Exception as e:
                         print(f"[Watchlist] Update error: {e}")
            
            time.sleep(3)