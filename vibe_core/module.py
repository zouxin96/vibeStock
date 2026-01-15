from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# Avoid circular imports by using TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .context import Context
    from .event import Event

class VibeModule(ABC):
    """
    Base class for all VibeStock modules.
    User modules must inherit from this class.
    """
    
    def __init__(self):
        self.context: Optional['Context'] = None
        self.config: Dict[str, Any] = {}
        self.name: str = self.__class__.__name__
        self.description: str = self.__class__.__doc__.strip() if self.__class__.__doc__ else ""

    def initialize(self, context: 'Context'):
        """
        Called when the module is loaded.
        Use this to read config, set up triggers, and initialize state.
        """
        self.context = context
        self.configure()

    def configure(self):
        """
        Optional: setup triggers or subscribe to topics here.
        This is a convenience method called by initialize.
        """
        pass

    def get_ui_config(self) -> Optional[Any]:
        """
        Returns UI configuration for this module.
        Can return a single Dict or a List[Dict] if the module provides multiple widgets.
        
        Return format example:
        {
            "id": "watchlist",           # Unique ID
            "component": "watchlist-widget", # Vue component name
            "title": "Market Watchlist", # Default title
            "default_col_span": "col-span-1",
            "script_path": "widget.js",   # Relative to module dir
            "config_default": {"codes": ["600519.SH"]}, # Default instance config
            "config_description": "JSON object with 'codes': list of stock codes." # Helper text
        }
        """
        return None

    @abstractmethod
    def on_event(self, event: 'Event'):
        """
        Core logic handler.
        Called whenever an event matching the module's subscription occurs.
        """
        pass

    def on_error(self, error: Exception):
        """
        Global error handler for this module.
        """
        if self.context and self.context.logger:
            self.context.logger.error(f"Module {self.name} error: {error}", exc_info=True)
        else:
            print(f"Module {self.name} error: {error}")

    def trigger_on_cron(self, cron_expression: str):
        """Helper to register a cron trigger"""
        # Logic to be implemented by the ModuleLoader/Context to interpret this
        # For now, we just store it in metadata or let Context handle registration
        if self.context:
            self.context.register_cron(self, cron_expression)

    def subscribe_topic(self, topic: str):
        """Helper to subscribe to a specific topic"""
        if self.context:
            self.context.subscribe(self, topic)
