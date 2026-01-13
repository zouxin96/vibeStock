from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTrigger(ABC):
    """
    Abstract base class for all triggers.
    """
    @abstractmethod
    def check(self, context) -> bool:
        """
        Evaluate if trigger should fire.
        (Note: For event-driven triggers, this might register callbacks instead)
        """
        pass

class IntervalTrigger(BaseTrigger):
    def __init__(self, seconds: int):
        self.seconds = seconds

class CronTrigger(BaseTrigger):
    def __init__(self, expression: str):
        self.expression = expression

class TopicTrigger(BaseTrigger):
    def __init__(self, topic: str):
        self.topic = topic
