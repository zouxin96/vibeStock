from vibe_core.module import VibeModule
from vibe_core.event import Event
from vibe_core.context import Context

class {{ModuleName}}(VibeModule):
    """
    {{Description}}
    """
    
    def __init__(self):
        super().__init__()
        self.description = "{{Description}}"

    def configure(self):
        # Configure triggers here
        # Example: self.trigger_on_cron("0 9 * * 1-5")
        # Example: self.subscribe_topic("quote.000001.SH")
        pass

    def on_event(self, event: Event):
        self.context.logger.info(f"{{ModuleName}} received event: {event}")
        
        # Your logic here
        # data = self.context.data.get_price(...)
