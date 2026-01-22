from vibe_core.module import VibeModule, ModuleCategory
import sys
import os
# Fix for dynamic loading relative imports
sys.path.append(os.path.dirname(__file__))
from adapter import AKShareAdapter
from base import AKShareBase 
import datetime

class AkShareDataModule(VibeModule, AKShareAdapter):
    # Trigger reload 3
    def __init__(self, context=None):
        VibeModule.__init__(self)
        AKShareBase.__init__(self) # Initialize the Data Provider base
        
        if context:
            self.context = context
            
        self.category = ModuleCategory.DATA
        self.name = "akshare_data"
        self.description = "Core Data Module for AKShare Adapter"
        self.error_count = 0

    def initialize(self, context):
        self.context = context
        
        # Dynamically register SELF as provider
        if self.context.data and hasattr(self.context.data, 'register_provider'):
             self.context.data.register_provider("akshare", self)
        
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