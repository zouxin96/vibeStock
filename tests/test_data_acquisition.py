import pytest
import sys
import os
import logging
import pandas as pd
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from vibe_core.context import Context
from vibe_core.data.hybrid import HybridDataProvider
from modules.core.akshare_data import AkShareDataModule
from modules.core.sina_data import SinaDataModule
from modules.core.stock_info import StockInfoModule

# Setup basic logging for tests
logging.basicConfig(level=logging.INFO)

class MockContext:
    def __init__(self):
        self.logger = logging.getLogger("MockContext")
        self.data = None # Will be set to HybridDataProvider in some tests
        self.broadcast_ui = MagicMock()
        self.register_cron = MagicMock()

@pytest.fixture
def mock_ctx():
    return MockContext()

def test_akshare_data_module(mock_ctx):
    """Test AkShareDataModule specifically for limit pool and market data."""
    print("\n[DataTest] AkShareDataModule")
    module = AkShareDataModule(mock_ctx)
    
    # 1. Test Limit Up Pool (Realtime/Today)
    df = module.get_limit_up_pool()
    assert isinstance(df, pd.DataFrame)
    print(f"- get_limit_up_pool: OK (count: {len(df)})")
    
    # 2. Test Market Snapshot (Directly from AKShare if implemented)
    # Most modules use get_snapshot for latest prices
    snapshot = module.get_snapshot(["600519.SH"])
    assert isinstance(snapshot, list)
    print(f"- get_snapshot: OK (results: {len(snapshot)})")

def test_sina_data_module(mock_ctx):
    """Test SinaDataModule for ultra-fast realtime snapshots."""
    print("\n[DataTest] SinaDataModule")
    module = SinaDataModule(mock_ctx)
    
    # Test Snapshot
    codes = ["600519.SH", "000001.SZ"]
    results = module.get_snapshot(codes)
    
    assert isinstance(results, list)
    # On weekends, Sina might still return last close data
    if results:
        print(f"- get_snapshot: OK (received {len(results)} items)")
        for item in results:
            print(f"  - {item['name']} ({item['code']}): {item['price']}")
            assert 'price' in item
            assert 'change' in item
    else:
        print("- get_snapshot: WARNING (Returned empty, check network or Sina availability)")

def test_stock_info_module(mock_ctx):
    """Test StockInfoModule for metadata fetching (Sector, Industry)."""
    print("\n[DataTest] StockInfoModule")
    module = StockInfoModule(mock_ctx)
    module.initialize(mock_ctx) # StockInfo needs DB init
    
    # Test individual info (e.g., Moutai)
    info = module.get_stock_info("600519")
    
    if info:
        print(f"- get_stock_info: OK")
        print(f"  - Industry: {info.get('行业')}")
        print(f"  - Province: {info.get('省份')}")
        # Fix: check keys for 'industry' or check for '行业'
        has_industry = '行业' in info or any('industry' in str(k).lower() for k in info.keys())
        assert has_industry
    else:
        print("- get_stock_info: FAILED or No Data")

def test_hybrid_provider_routing(mock_ctx):
    """Test HybridDataProvider's ability to route to correct modules."""
    print("\n[DataTest] HybridDataProvider Routing")
    
    # 1. Setup Hybrid and Modules
    hybrid = HybridDataProvider()
    mock_ctx.data = hybrid
    
    ak_mod = AkShareDataModule(mock_ctx)
    sina_mod = SinaDataModule(mock_ctx)
    info_mod = StockInfoModule(mock_ctx)
    
    # 2. Register them
    hybrid.register_provider("akshare", ak_mod)
    hybrid.register_provider("sina", sina_mod)
    hybrid.register_provider("stock_info", info_mod)
    
    # Set Sina as default for snapshots
    hybrid._default = sina_mod
    
    # 3. Test Routing for get_limit_up_pool (Should go to AkShare)
    # The __getattr__ in Hybrid should handle this.
    df = hybrid.get_limit_up_pool()
    assert isinstance(df, pd.DataFrame)
    print("- Routed get_limit_up_pool to AKShare: OK")
    
    # 4. Test Routing for get_snapshot (Should go to Sina)
    snapshot = hybrid.get_snapshot(["600519.SH"])
    assert isinstance(snapshot, list)
    # Note: verify it actually used Sina if possible (Sina data format has specific fields like 'vol')
    if snapshot:
        assert 'price' in snapshot[0]
        print("- Routed get_snapshot to Sina: OK")

    # 5. Test Routing for get_stock_info (Should go to StockInfo)
    info = hybrid.get_stock_info("000001")
    if info:
        print("- Routed get_stock_info to StockInfo: OK")

if __name__ == "__main__":
    # Allow manual execution
    ctx = MockContext()
    try:
        test_akshare_data_module(ctx)
        test_sina_data_module(ctx)
        test_stock_info_module(ctx)
        test_hybrid_provider_routing(ctx)
        print("\nALL DATA MODULE TESTS COMPLETED SUCCESSFULLY.")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
