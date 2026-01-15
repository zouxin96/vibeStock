from typing import Any, Callable, Dict, List
import logging
from .module import VibeModule
from .storage import CSVStorageService

# Import singleton manager. Note: This creates a dependency on vibe_server.
# In a strictly decoupled architecture we might use dependency injection,
# but for this scale, direct import is fine.
try:
    from vibe_server.websocket_manager import manager as ws_manager
except ImportError:
    ws_manager = None

class OutputManager:
    def __init__(self):
        self.logger = logging.getLogger("vibe.output")
        self._setup_logging()

    def _setup_logging(self):
        # Configure root-ish logger for vibe
        logger = logging.getLogger("vibe")
        logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers if re-initialized
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
            # Console Handler
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            
            # File Handler
            fh = logging.FileHandler("vibe_system.log", encoding='utf-8')
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    def dashboard(self, widget_id: str, data: Any):
        """
        Push data to the dashboard widget.
        """
        if ws_manager:
            message = {
                "type": "update",
                "widget_id": widget_id,
                "data": data
            }
            ws_manager.broadcast_sync(message)
        else:
            self.logger.warning("WebSocket manager not available. Dashboard update skipped.")

    def notify(self, message: str):
        self.logger.info(f"[NOTIFY]: {message}")

class Context:
    """
    Context object passed to all modules.
    Provides access to Data, Output, Logger, and System Services.
    """
    def __init__(self):
        self.data: Any = None  # Placeholder for DataProvider
        self.output = OutputManager() 
        self.logger: logging.Logger = logging.getLogger("vibe")
        self.storage = CSVStorageService() # Initialize Storage Service
        self.state: Dict[str, Any] = {} # Persistent state storage
        self._scheduler: Any = None
        self._event_bus: Any = None
        self._module_registry: Dict[str, VibeModule] = {}

    def register_module_instance(self, module_id: str, instance: VibeModule):
        """Register a module instance to handle messages for a specific ID."""
        self._module_registry[module_id] = instance
        self.logger.info(f"Registered module route: {module_id} -> {instance.name}")

    def broadcast_ui(self, widget_id: str, data: Any):
        """
        Broadcast data to a specific UI widget.
        """
        self.output.dashboard(widget_id, data)
        
    async def handle_client_message(self, message: Dict):
        """
        Route message from WebSocket to appropriate module.
        Expected msg: { "moduleId": "...", ... }
        """
        module_id = message.get("moduleId")
        if not module_id: return

        if module_id in self._module_registry:
            module = self._module_registry[module_id]
            if hasattr(module, 'on_client_message'):
                # Run in thread pool to avoid blocking async loop?
                # on_client_message is likely synchronous.
                # Use simple call for now, but ideally offload.
                try:
                    module.on_client_message(message)
                except Exception as e:
                    self.logger.error(f"Error handling client message in {module.name}: {e}")
        else:
            self.logger.warning(f"No module registered for ID: {module_id}")

    def register_cron(self, module: VibeModule, cron_expr: str):
        """Register a cron job for the module"""
        if self._scheduler:
            # SimpleScheduler uses interval in seconds, Cron is complex.
            # For this prototype, if cron_expr starts with 'interval:', we parse seconds.
            # e.g. "interval:5"
            if cron_expr.startswith("interval:"):
                try:
                    seconds = int(cron_expr.split(":")[1])
                    # Create a wrapper that injects a Timer event
                    def trigger():
                        from .event import Event
                        import time
                        evt = Event("TIMER", "cron", {}, time.time())
                        module.on_event(evt)
                    
                    # Pass module.name as tag for cleanup later
                    self._scheduler.add_interval_job(trigger, seconds, tag=module.name)
                    self.logger.info(f"Registered interval job {seconds}s for {module.name}")
                except Exception as e:
                    self.logger.error(f"Failed to parse interval: {e}")
            else:
                 self.logger.warning(f"Complex cron '{cron_expr}' not supported in SimpleScheduler. Use 'interval:N'.")

    def deregister_module(self, module_name: str):
        """
        Cleanup resources associated with a module.
        """
        self.logger.info(f"Deregistering module resources for: {module_name}")
        
        # 1. Cancel Scheduled Jobs
        if self._scheduler:
            self._scheduler.cancel_jobs(module_name)
            
        # 2. (Future) Unsubscribe from EventBus
        # if self._event_bus: self._event_bus.unsubscribe_all(module_name)

    def subscribe(self, module: VibeModule, topic: str):
        """Subscribe module to a topic"""
        # In a real implementation, this would delegate to self._event_bus
        self.logger.info(f"Subscribed {module.name} to '{topic}'")

    @property
    def now(self):
        """
        Returns the current system time.
        In Backtest mode, this returns the simulated time.
        """
        import datetime
        return datetime.datetime.now()
