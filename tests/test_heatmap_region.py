import pytest
import sys
import os
import logging
import pandas as pd
import time
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from vibe_core.context import Context
from vibe_core.data.hybrid import HybridDataProvider
from modules.core.akshare_data import AkShareDataModule
from modules.core.stock_info import StockInfoModule
from modules.beta.region_pie import RegionPieModule
from modules.beta.market_heatmap import MarketHeatmapModule

# Setup basic logging
logging.basicConfig(level=logging.INFO)

class MockContext:
    def __init__(self):
        self.logger = logging.getLogger("MockContext")
        self.data = None 
        self.broadcast_ui = MagicMock()
        self.register_cron = MagicMock()

@pytest.fixture
def full_ctx():
    ctx = MockContext()
    hybrid = HybridDataProvider()
    ctx.data = hybrid
    
    ak_mod = AkShareDataModule(ctx)
    info_mod = StockInfoModule(ctx)
    info_mod.initialize(ctx)
    
    hybrid.register_provider("akshare", ak_mod)
    hybrid.register_provider("stock_info", info_mod)
    
    return ctx

def test_region_pie_module(full_ctx):
    print("\n[ModuleTest] RegionPieModule")
    module = RegionPieModule(full_ctx)
    
    # Run process
    module.process()
    
    if full_ctx.broadcast_ui.called:
        # Find the call for region_pie
        calls = [c for c in full_ctx.broadcast_ui.call_args_list if c[0][0] == "region_pie"]
        if calls:
            payload = calls[0][0][1]
            print(f"- region_pie broadcasted {len(payload)} regions.")
            if payload:
                print(f"  Example: {payload[0]}")
                assert "name" in payload[0]
                assert "value" in payload[0]
        else:
            print("- region_pie did not broadcast (likely no limit-up data).")
    else:
        print("- No broadcast at all.")

def test_market_heatmap_module(full_ctx):
    print("\n[ModuleTest] MarketHeatmapModule")
    
    # Debug: Check if data provider has the method
    has_method = hasattr(full_ctx.data, 'get_em_sectors')
    print(f"- Data provider has get_em_sectors: {has_method}")
    
    if has_method:
        df = full_ctx.data.get_em_sectors()
        print(f"- get_em_sectors returned {len(df) if df is not None else 'None'} records.")
        if df is not None and not df.empty:
            print(f"  Columns: {df.columns.tolist()}")

    module = MarketHeatmapModule(full_ctx)
    
    # Run process
    module.process()
    
    if full_ctx.broadcast_ui.called:
        calls = [c for c in full_ctx.broadcast_ui.call_args_list if c[0][0] == "market_heatmap"]
        if calls:
            payload = calls[0][0][1]
            print(f"- market_heatmap broadcasted {len(payload)} sectors.")
            if payload:
                print(f"  Example: {payload[0]}")
                assert "name" in payload[0]
                assert "change" in payload[0]
        else:
            print("- market_heatmap did not broadcast.")
    else:
         print("- No broadcast at all.")

if __name__ == "__main__":
    ctx = full_ctx()
    try:
        test_region_pie_module(ctx)
    except Exception as e:
        print(f"RegionPie Test Failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        test_market_heatmap_module(ctx)
    except Exception as e:
        print(f"Heatmap Test Failed: {e}")
        import traceback
        traceback.print_exc()
