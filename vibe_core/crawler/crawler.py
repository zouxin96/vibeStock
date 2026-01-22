from abc import ABC, abstractmethod
from typing import Any, List, Dict
import os
import datetime

class BaseCrawler(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def crawl(self) -> List[Any]:
        """
        Execute crawl logic.
        Returns a list of raw content objects (e.g., dicts, file paths).
        """
        pass

    def save_raw(self, content: Any, prefix: str = "raw") -> str:
        """
        Helper to save raw content to disk.
        """
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        save_dir = os.path.join("storage", "raw", date_str)
        os.makedirs(save_dir, exist_ok=True)
        
        filename = f"{prefix}_{int(datetime.datetime.now().timestamp())}.txt"
        filepath = os.path.join(save_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(content))
            
        return filepath
