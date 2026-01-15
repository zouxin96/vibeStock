from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# Avoid circular imports by using TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .context import Context
    from .event import Event

class VibeModule(ABC):
    """
    VibeStock 模块基类。
    所有用户自定义模块必须继承此类。
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
        模块加载时调用。
        用于读取配置、设置触发器和初始化状态。
        Called when the module is loaded.
        Use this to read config, set up triggers, and initialize state.
        """
        self.context = context
        self.configure()

    def configure(self):
        """
        可选：在此处设置触发器或订阅主题。
        这是由 initialize 调用的便捷方法。
        Optional: setup triggers or subscribe to topics here.
        This is a convenience method called by initialize.
        """
        pass

    def get_ui_config(self) -> Optional[Any]:
        """
        返回此模块的 UI 配置。
        可以返回单个字典，如果模块提供多个组件，则返回字典列表 List[Dict]。
        
        返回格式示例 (Return format example):
        {
            "id": "watchlist",           # 唯一 ID
            "component": "watchlist-widget", # Vue 组件名称
            "title": "Market Watchlist", # 默认标题
            "default_col_span": "col-span-1",
            "script_path": "widget.js",   # 相对于模块目录的路径
            "config_default": {"codes": ["600519.SH"]}, # 默认实例配置
            "config_description": "JSON object with 'codes': list of stock codes." # 帮助文本
        }
        """
        return None

    @abstractmethod
    def on_event(self, event: 'Event'):
        """
        核心逻辑处理程序。
        每当发生与模块订阅匹配的事件时调用。
        Core logic handler.
        Called whenever an event matching the module's subscription occurs.
        """
        pass

    def on_error(self, error: Exception):
        """
        此模块的全局错误处理程序。
        Global error handler for this module.
        """
        if self.context and self.context.logger:
            self.context.logger.error(f"Module {self.name} error: {error}", exc_info=True)
        else:
            print(f"Module {self.name} error: {error}")

    def trigger_on_cron(self, cron_expression: str):
        """
        辅助方法：注册 Cron 定时触发器
        Helper to register a cron trigger
        """
        # Logic to be implemented by the ModuleLoader/Context to interpret this
        # For now, we just store it in metadata or let Context handle registration
        if self.context:
            self.context.register_cron(self, cron_expression)

    def subscribe_topic(self, topic: str):
        """
        辅助方法：订阅特定主题
        Helper to subscribe to a specific topic
        """
        if self.context:
            self.context.subscribe(self, topic)
