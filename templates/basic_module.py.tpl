from vibe_core.module import VibeModule
from vibe_core.event import Event

class {{ModuleName}}(VibeModule):
    """
    {{Description}}
    """
    
    def __init__(self, context=None):
        super().__init__(context)
        self.id = "{{MODULE_ID}}"
        self.name = "{{MODULE_NAME}}"

    def on_start(self):
        if not self.context: return
        self.logger.info(f"{self.name} started.")
        # self.context.register_cron(self, "interval:60")

    def on_stop(self):
        self.logger.info(f"{self.name} stopped.")

    def on_event(self, event: Event):
        pass

    @classmethod
    def get_ui_config(cls):
        """
        Return UI configuration for the dashboard.
        Should match the structure expected by ui/widgets.js or define a new component.
        """
        return None
        # Example:
        # return {
        #     "id": "{{MODULE_ID}}",
        #     "title": "{{MODULE_NAME}}",
        #     "component": "base-list-widget", # or custom
        #     "config_default": {},
        #     "script_path": "widget.js" # if custom component
        # }