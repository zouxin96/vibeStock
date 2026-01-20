from typing import Any, Dict, Type
from .provider import IDataProvider
from .aggregator import DataAggregator
from .hybrid import HybridDataProvider

class DataFactory:
    _registry: Dict[str, Type[IDataProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: Type[IDataProvider]):
        cls._registry[name] = provider_cls

    @classmethod
    def get_registered_providers(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def _instantiate(cls, provider_type: str, config: Dict[str, Any]) -> IDataProvider:
        """Helper to instantiate a single provider with aggregator."""
        provider_cls = cls._registry.get(provider_type)
        if not provider_cls:
            return None # Or raise
            
        # Constructor args
        provider = None
        if provider_type == "local":
            provider = provider_cls(root_path="tushare")
        elif provider_type == "tushare" or provider_type == "tushare_info":
            token = config.get("data", {}).get("tushare_token", "")
            provider = provider_cls(token=token)
        elif provider_type == "stock_info":
            # StockInfoAdapter default constructor uses default path, can be customized here if needed
            provider = provider_cls()
        else:
            provider = provider_cls() # akshare, sina, limit_board
            
        # Wrap with Aggregator
        cache_ttl = config.get("data", {}).get("cache_ttl", 5)
        return DataAggregator(provider, cache_ttl=cache_ttl)

    @classmethod
    def create_provider(cls, config: Dict[str, Any]) -> IDataProvider:
        """
        Create a Hybrid Data Provider that manages multiple sources.
        """
        data_config = config.get("data", {})
        
        # 1. Determine Default Provider
        # Prefer 'sina' for realtime if not specified, unless in backtest
        mode = config.get("system", {}).get("mode", "live")
        default_type = data_config.get("provider", "sina") 
        
        if mode == "backtest":
            default_type = "local"
        
        default_provider = cls._instantiate(default_type, config)
        if not default_provider:
             raise ValueError(f"Default provider '{default_type}' not found.")

        # 2. Instantiate Secondary Providers (AKShare, Tushare, etc.)
        # We always load 'akshare' if available as a powerful fallback/extension
        # We load 'tushare' if token is present
        providers = {}
        
        # Add default to map too (for explicit routing)
        providers[default_type] = default_provider
        
        # Auto-load AKShare if it's not default
        if default_type != "akshare" and "akshare" in cls._registry:
            ak_instance = cls._instantiate("akshare", config)
            if ak_instance:
                providers["akshare"] = ak_instance

        # Auto-load Tushare if token exists and not default
        token = data_config.get("tushare_token")
        if token and default_type != "tushare" and "tushare" in cls._registry:
             ts_instance = cls._instantiate("tushare", config)
             if ts_instance:
                 providers["tushare"] = ts_instance

        # Auto-load StockInfoAdapter (Specialized)
        if "stock_info" in cls._registry:
            info_instance = cls._instantiate("stock_info", config)
            if info_instance:
                providers["stock_info"] = info_instance

        # 3. Create Hybrid Provider
        # Load custom routing from config if any
        routing = data_config.get("routing", {})
        
        # Add default routing for get_stock_info to stock_info adapter
        if "get_stock_info" not in routing:
            routing["get_stock_info"] = "stock_info"
        
        return HybridDataProvider(default_provider, providers, routing)

# Register built-ins

# Import from new categorized folders
from .adapter.realtime.local import LocalFileAdapter
from .adapter.stock_detail.tushare import TushareAdapter
from .adapter.realtime.sina import SinaLiveAdapter
from .adapter.stock_detail.tushare_info import TushareInfoAdapter
from .adapter.stock_detail.info import StockInfoAdapter

# AKShare Combined Adapter (still needed for backward compatibility in factory logic)
from .adapter.akshare_adapter import AKShareAdapter
# If we wanted to register components separately, we could, but HybridProvider logic uses 'akshare' as a bundle.
# So we keep AKShareAdapter as the entry point for 'akshare'.

# AKShare Limit Board (can be registered separately if needed, but usually accessed via AKShareAdapter)
from .adapter.realtime.akshare_limit import AKShareLimitBoard as LimitBoardAdapter

DataFactory.register("local", LocalFileAdapter)
DataFactory.register("tushare", TushareAdapter)
DataFactory.register("sina", SinaLiveAdapter)
DataFactory.register("akshare", AKShareAdapter)
DataFactory.register("tushare_info", TushareInfoAdapter)
DataFactory.register("limit_board", LimitBoardAdapter)
DataFactory.register("stock_info", StockInfoAdapter)
