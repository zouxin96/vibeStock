from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, raw_content: Any) -> Dict[str, Any]:
        """
        Process raw content and return structured signals.
        Example output: {'sentiment': 0.8, 'keywords': ['Apple', 'iPhone']}
        """
        pass

class DummyAnalyzer(BaseAnalyzer):
    def analyze(self, raw_content: Any):
        return {"summary": "Analyzed content", "raw_length": len(str(raw_content))}
