from vibe_core.module import VibeModule
from vibe_core.event import Event
from vibe_core.data.factory import DataFactory
import time
import threading

class WatchlistModule(VibeModule):
    """
    Monitors a list of stocks using Sina Data Source (Realtime).
    Standard Multi-Instance capable module.
    # Trigger reload
    """
    dependencies = ['SinaDataModule']
    
    def configure(self):
        self.running = True
        # Read codes from config (default provided if missing)
        self.codes = self.config.get("codes", ["600519.SH", "000001.SZ", "600036.SH"])
        if isinstance(self.codes, str):
            self.codes = [c.strip() for c in self.codes.split(',')]
            
        # Normalize immediately
        self.codes = [self._normalize_code(c) for c in self.codes if c]
        
        try:
            self.adapter = DataFactory.create_provider({"data": {"provider": "sina"}})
        except Exception as e:
            print(f"[Watchlist] Failed to create Sina adapter: {e}")
            self.adapter = None

        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def get_ui_config(self):
        # We return a generic ID. The ModuleLoader will append instance ID if needed.
        # But wait, ModuleLoader logic: if instance.name != class_name, it appends.
        # Let's use a base ID "watchlist".
        return {
            "id": "watchlist", 
            "component": "watchlist-widget",
            "title": "Market Watchlist",
            "default_col_span": "col-span-1 md:col-span-2 lg:col-span-1",
            "script_path": "widget.js",
            "config_default": {
                "codes": ["600519.SH"]
            },
            "config_description": "List of stock codes to monitor."
        }

    def on_event(self, event: Event):
        pass
        
    def _normalize_code(self, code: str) -> str:
        code = code.strip().upper()
        if '.' in code: return code
        
        if code.startswith(('6', '900', '688', '689')): return f"{code}.SH"
        if code.startswith(('0', '2', '3')): return f"{code}.SZ"
        if code.startswith(('4', '8', '920')): return f"{code}.BJ"
        if code == '000001': return '000001.SH'
        return code 

    def on_client_message(self, message: dict):
        """
        Handle runtime config updates from UI.
        """
        msg_type = message.get("type")
        
        if msg_type == "update_config":
            config = message.get("config", {})
            new_codes = config.get("codes")
            if new_codes:
                if isinstance(new_codes, str):
                    new_codes = [c.strip() for c in new_codes.split(',')]
                
                self.codes = [self._normalize_code(c) for c in new_codes if c]
                self.context.logger.info(f"[{self.name}] Updated codes: {self.codes}")
                # Trigger immediate update?
                pass

    def _update_loop(self):
        while self.running:
            if self.adapter and self.codes:
                try:
                    data_list = self.adapter.get_snapshot(self.codes)
                    
                    # Map back to display preference if needed, but here we just push what we got
                    # The widget ID to broadcast to is THIS instance's registered ID.
                    # Which ModuleLoader registers as self.get_ui_config()['id'] (potentially patched)
                    
                    # Issue: How do we know the 'patched' widget ID assigned by ModuleLoader?
                    # ModuleLoader registered context.register_module_instance(widget_id, self).
                    # But it didn't tell US what that ID is.
                    # We should probably iterate or broadcast to a topic?
                    # Or ModuleLoader should have set 'self.widget_id' on us?
                    
                    # Simplification: Broadcast to 'watchlist' topic suffix?
                    # Or just rely on the fact that if instance name is 'watchlist_tech',
                    # ModuleLoader likely registered 'watchlist_watchlist_tech'.
                    
                    # BETTER: Use self.name as the channel ID?
                    # The frontend widget will subscribe to 'moduleId'.
                    # If we follow the convention that `get_ui_config()['id']` IS the channel...
                    
                    # Let's assume ModuleLoader patch logic:
                    # if instance.name != class_name: cfg['id'] = f"{cfg['id']}_{instance.name}"
                    
                    target_id = "watchlist"
                    if self.name != "WatchlistModule":
                        # If name is customized, ID is patched
                        target_id = f"watchlist_{self.name}"
                        
                    # NOTE: This coupling with ModuleLoader's patching logic is fragile.
                    # Ideally, ModuleLoader sets `self.ui_id` on the instance.
                    
                    self.context.broadcast_ui(target_id, data_list)
                                    
                except Exception as e:
                     print(f"[{self.name}] Update error: {e}")
            
            time.sleep(3)