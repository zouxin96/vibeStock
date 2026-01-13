from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time

@dataclass
class Event:
    """
    Standard Event definition for VibeStock system.
    """
    event_type: str  # e.g., 'TIMER', 'QUOTE', 'NEWS', 'LIFECYCLE'
    topic: str       # e.g., 'market.open', '000001.SH', 'news.sina'
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def __str__(self):
        return f"<Event type={self.event_type} topic={self.topic} ts={self.timestamp}>"
