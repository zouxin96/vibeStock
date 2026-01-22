import logging
import pandas as pd
from typing import Optional, List, Dict, Any
from .provider import IDataProvider, DataDimension, SyncPolicy, DataCategory

class HybridDataProvider(IDataProvider):
    """
    混合数据提供者 (Hybrid Data Provider)
    作为一个 Facade，根据方法名或数据类型将请求路由到最佳的底层数据源。
    """
    
    def __init__(self, default_provider: IDataProvider = None, providers: Dict[str, IDataProvider] = None, routing: Dict[str, str] = None):
        """
        :param default_provider: 默认数据源 (通常是实时性最好的，如 Sina)
        :param providers: 所有可用数据源字典 { 'akshare': instance, 'tushare': instance, ... }
        :param routing: 路由规则 { 'method_name': 'provider_key' }
        """
        self.logger = logging.getLogger("vibe.data.hybrid")
        self._default = default_provider
        self._providers = providers or {}
        self._routing = routing or {}
        
        # 内置默认路由规则 (如果配置未覆盖)
        # 优先使用 AKShare 处理板块、涨跌停、历史数据
        self._default_routing = {
            # AKShare 特有
            "get_limit_up_pool": "akshare",
            "get_broken_limit_pool": "akshare",
            "get_limit_down_pool": "akshare",
            "get_pseudo_limit_pool": "akshare",
            "get_ths_concepts": "akshare",
            "get_em_concepts": "akshare",
            "get_concept_cons": "akshare",
            "get_full_snapshot": "akshare",
            "sync_daily_data": "akshare",
            "sync_limit_data": "akshare",
            "get_em_sectors": "akshare", # Added explicit routing
            
            # Stock Info (Snowball via AKShare)
            "get_stock_info": "stock_info",
            
            # Tushare 特有 (如有)
            "get_income": "tushare",
            
            # 基础接口通常走 Default (Sina)，但如果 Default 不支持，可以 fallback
            # "get_snapshot": "default", 
            # "get_price": "default"
        }
        
        # 合并路由: 用户配置优先
        for method, provider in self._default_routing.items():
            if method not in self._routing:
                self._routing[method] = provider

    @property
    def data_dimension(self) -> DataDimension:
        return self._default.data_dimension if self._default else DataDimension.TICK

    @property
    def sync_policy(self) -> SyncPolicy:
        return self._default.sync_policy if self._default else SyncPolicy.REALTIME

    @property
    def archive_filename_template(self) -> str:
        return self._default.archive_filename_template if self._default else "data_{date}.csv"

    def register_provider(self, name: str, provider: IDataProvider):
        """Dynamically register a data provider."""
        self._providers[name] = provider
        self.logger.info(f"Registered data provider: {name}")
        # If no default set and this is a good candidate (e.g. sina), set it?
        # For now, let's keep explicit default setting or first one.
        if not self._default:
            self.logger.info(f"Setting {name} as temporary default provider.")
            self._default = provider

    def _get_provider_for(self, method_name: str) -> IDataProvider:
        """根据路由规则决定使用哪个 Provider"""
        provider_key = self._routing.get(method_name)
        
        if provider_key:
            if provider_key in self._providers:
                # self.logger.debug(f"Routing {method_name} to {provider_key}")
                return self._providers[provider_key]
            else:
                self.logger.warning(f"Routed {method_name} to {provider_key} but provider not found. Using default.")
        
        if self._default:
            return self._default
            
        # Last resort: Try to find ANY provider that has this method (safe for standard calls)
        for p in self._providers.values():
            if hasattr(p, method_name):
                return p
                
        raise RuntimeError("No data provider available to handle request.")

    # --- 接口实现 ---

    def get_price(self, code: str, date: str = None) -> Optional[float]:
        try:
            return self._get_provider_for("get_price").get_price(code, date)
        except: return None

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            return self._get_provider_for("get_history").get_history(code, start_date, end_date)
        except: return pd.DataFrame()

    def get_snapshot(self, codes: List[str]) -> List[dict]:
        try:
            return self._get_provider_for("get_snapshot").get_snapshot(codes)
        except: return []

    def get_table(self, table_name: str, date: Optional[str] = None) -> pd.DataFrame:
        try:
            return self._get_provider_for("get_table").get_table(table_name, date)
        except: return pd.DataFrame()

    # --- 魔法转发 ---
    def __getattr__(self, name):
        """
        转发未知方法到对应的 Provider。
        1. 查路由表
        2. 如果路由表没配置，检查 Default 是否有该方法
        3. 如果 Default 没有，遍历其他 Provider 谁有就用谁 (Auto Discovery)
        """
        # 1. Routing
        if name in self._routing:
            target = self._get_provider_for(name)
            return getattr(target, name)
            
        # 2. Default
        if self._default and hasattr(self._default, name):
            return getattr(self._default, name)
            
        # 3. Auto Discovery (Failover)
        # 这允许我们在不配置路由的情况下调用 akshare 特有的方法 (如 get_limit_up_pool)
        for key, provider in self._providers.items():
            if hasattr(provider, name):
                # 缓存这个发现，下次直接路由
                self._routing[name] = key
                # self.logger.info(f"Auto-routed method '{name}' to provider '{key}'")
                return getattr(provider, name)
        
        # Avoid returning None implicitly if not found, raise Error as expected by Python data model
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}' and no sub-provider has it.")

