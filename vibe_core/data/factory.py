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
            
        # New Module-based instantiation (No args)
        try:
            provider = provider_cls()
        except TypeError:
            # Fallback for legacy classes if any
            provider = provider_cls() 

        # Manual configuration injection since we don't have a Context here yet
        # (The provider will be attached to context later, or modules will re-register themselves)
        
        if provider_type == "local":
            # Backward compat: LocalDataModule defaults to 'tushare'
            pass
            
        elif provider_type == "tushare" or provider_type == "tushare_info":
            token = config.get("data", {}).get("tushare_token", "")
            if hasattr(provider, 'token'):
                provider.token = token
                # Manually trigger init if needed, though usually done in initialize(context)
                if hasattr(provider, '_init_tushare'):
                    provider._init_tushare()

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

# Import from new modules (Replacing adapters)
import sys
import os
# Ensure project root is in path to find modules
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from modules.core.local_data import LocalDataModule as LocalFileAdapter
from modules.core.tushare_data import TushareDataModule as TushareAdapter
# TushareDataModule handles both market and info, so reuse for Info
from modules.core.tushare_data import TushareDataModule as TushareInfoAdapter 
from modules.core.sina_data import SinaDataModule as SinaLiveAdapter
from modules.core.stock_info import StockInfoModule as StockInfoAdapter
from modules.core.akshare_data import AkShareDataModule as AKShareAdapter

# LimitBoard is now part of AKShareDataModule
LimitBoardAdapter = AKShareAdapter

DataFactory.register("local", LocalFileAdapter)
DataFactory.register("tushare", TushareAdapter)
DataFactory.register("sina", SinaLiveAdapter)
DataFactory.register("akshare", AKShareAdapter)
DataFactory.register("tushare_info", TushareInfoAdapter)
DataFactory.register("limit_board", LimitBoardAdapter)
DataFactory.register("stock_info", StockInfoAdapter)
