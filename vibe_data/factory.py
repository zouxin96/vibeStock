from typing import Any, Dict, Type
from .provider import IDataProvider
from .aggregator import DataAggregator

class DataFactory:
    _registry: Dict[str, Type[IDataProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: Type[IDataProvider]):
        cls._registry[name] = provider_cls

    @classmethod
    def get_registered_providers(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def create_provider(cls, config: Dict[str, Any]) -> IDataProvider:
        # 1. Check if specific provider type is requested in config
        provider_type = config.get("data", {}).get("provider")
        
        # 2. If not specified, infer from mode
        if not provider_type:
            mode = config.get("system", {}).get("mode", "live")
            if mode == "backtest":
                provider_type = "local"
            else:
                # Default to local if tushare token not set, else tushare? 
                # For simplicity, default to 'local' or 'tushare' based on logic
                # Let's default to local for safety if not configured
                provider_type = "local"

        # 3. Instantiate
        provider_cls = cls._registry.get(provider_type)
        if not provider_cls:
            raise ValueError(f"Data provider '{provider_type}' not registered. Available: {list(cls._registry.keys())}")
            
        # 4. Pass config to constructor (assuming common init interface or handling kwargs)
        provider = None
        if provider_type == "local":
            provider = provider_cls(root_path="tushare")
        elif provider_type == "tushare" or provider_type == "tushare_info":
            token = config.get("data", {}).get("tushare_token", "")
            provider = provider_cls(token=token)
        elif provider_type == "akshare":
            provider = provider_cls()
        else:
            provider = provider_cls()

        # 5. Wrap with DataAggregator for request coalescing and caching
        # Check config if caching is disabled (optional, defaulting to enabled)
        # Assuming config['data']['cache_ttl'] exists, default to 5s
        cache_ttl = config.get("data", {}).get("cache_ttl", 5)
        return DataAggregator(provider, cache_ttl=cache_ttl)

# Register built-ins

from .adapter.local_adapter import LocalFileAdapter
from .adapter.tushare_adapter import TushareAdapter
from .adapter.sina_adapter import SinaLiveAdapter
from .adapter.akshare import AKShareAdapter
from .adapter.tushare_info_adapter import TushareInfoAdapter
from .adapter.akshare.limit_board import AKShareLimitBoard as LimitBoardAdapter

DataFactory.register("local", LocalFileAdapter)
DataFactory.register("tushare", TushareAdapter)
DataFactory.register("sina", SinaLiveAdapter)
DataFactory.register("akshare", AKShareAdapter)
DataFactory.register("tushare_info", TushareInfoAdapter)
DataFactory.register("limit_board", LimitBoardAdapter)
