from vibe_core.module import VibeModule, ModuleCategory
from .adapter import AKShareAdapter
import datetime

class AkShareDataModule(VibeModule):
    def __init__(self):
        super().__init__()
        self.category = ModuleCategory.DATA
        self.name = "akshare_data"
        self.description = "Core Data Module for AKShare Adapter"
        self.adapter = None
        self.error_count = 0

    def initialize(self, context):
        self.context = context
        self.adapter = AKShareAdapter()
        
        # Dynamically register to HybridDataProvider
        if self.context.data and hasattr(self.context.data, 'register_provider'):
             self.context.data.register_provider("akshare", self.adapter)
        
        # Periodic status update (every 5 seconds)
        self.trigger_on_cron("interval:5")
        
        self.configure()
        self.on_start()

    def on_event(self, event):
        # Broadcast status every interval
        self.broadcast_status()

    def broadcast_status(self):
        # In a real scenario, we'd pull stats from the adapter
        status = {
            "is_connected": True, 
            "last_updated": datetime.datetime.now().strftime("%H:%M:%S"),
            "request_count": 0, 
            "error_count": self.error_count
        }
        self.context.broadcast_ui("akshare_status", status)

    def get_ui_config(self):
        return {
            "id": "akshare_status",
            "component": "akshare-monitor-widget", 
            "title": "AKShare Status",
            "default_col_span": "col-span-1",
            "script_path": "widget.js" 
        }