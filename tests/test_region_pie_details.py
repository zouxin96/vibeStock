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

# Configure logging to show info from modules
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

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

def test_region_pie_completeness(full_ctx):
    print("\n[DetailTest] RegionPie Completeness")
    module = RegionPieModule(full_ctx)
    
    # 1. First Pass
    print("--- First Pass (Process) ---")
    module.process()
    
    # Check what was broadcasted
    if full_ctx.broadcast_ui.called:
        payload = full_ctx.broadcast_ui.call_args[0][1]
        total_mapped = sum(item['value'] for item in payload)
        print(f"First Pass: Broadcasted {len(payload)} regions, Total Stocks Mapped: {total_mapped}")
    else:
        print("First Pass: No broadcast.")
        
    # 2. Wait for Background Thread (Simulate)
    # The module spawns a thread to fetch missing info. 
    # We can't easily join that thread since we don't have a handle to it in the test,
    # but we can check if data is being fetched by monitoring the log or checking the DB.
    
    print("--- Waiting 5s for background fetch ---")
    time.sleep(5)
    
    # 3. Second Pass
    print("--- Second Pass (Process) ---")
    module.process()
    
    if full_ctx.broadcast_ui.called:
        # Get the LATEST call
        payload = full_ctx.broadcast_ui.call_args[0][1] 
        total_mapped = sum(item['value'] for item in payload)
        print(f"Second Pass: Broadcasted {len(payload)} regions, Total Stocks Mapped: {total_mapped}")
        
        # Verify coverage
        df_limit = full_ctx.data.get_limit_up_pool()
        total_limit = len(df_limit) if df_limit is not None else 0
        print(f"Total Limit Up Stocks: {total_limit}")
        
        if total_limit > 0:
            coverage = total_mapped / total_limit
            print(f"Coverage: {coverage:.2%}")
            
            # We expect coverage to improve or be high
            if coverage < 0.5:
                print("WARNING: Low coverage (<50%). Check fetch_missing_info logic.")
            else:
                print("SUCCESS: Good coverage.")

if __name__ == "__main__":
    ctx = full_ctx()
    test_region_pie_completeness(ctx)
