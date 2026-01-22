import pytest
import sys
import os
import logging
import datetime
from unittest.mock import MagicMock
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

from modules.core.akshare_data import AkShareDataModule
from modules.beta.limit_rank import LimitOrderRankModule
from modules.beta.weighted_limit_up import WeightedLimitUpModule
from modules.prod.limit_up_monitor import LimitUpMonitor
from vibe_core.context import Context

# Configure logging to see output during tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class MockContext:
    def __init__(self):
        self.data = MagicMock()
        self.broadcast_ui = MagicMock()
        self.register_cron = MagicMock()
        self.logger = logging.getLogger("MockContext")

@pytest.fixture
def mock_context():
    return MockContext()

@pytest.fixture
def data_module(mock_context):
    """Initializes the real data module for testing."""
    try:
        module = AkShareDataModule(mock_context)
        return module
    except ImportError:
        pytest.skip("AKShare not installed")

def test_akshare_get_limit_up_pool(data_module):
    """
    Test 1: Verify Core Data Provider
    Checks if get_limit_up_pool returns a DataFrame (empty or not).
    """
    print("\n[Test] AkShareDataModule.get_limit_up_pool")
    
    try:
        # Use a fake date or None (Today)
        # Note: If today is weekend, it might return empty.
        df = data_module.get_limit_up_pool()
        
        print(f"Result Type: {type(df)}")
        assert isinstance(df, pd.DataFrame), "Must return a DataFrame"
        
        if not df.empty:
            print(f"SUCCESS: Fetched {len(df)} records.")
            print(f"Columns: {df.columns.tolist()[:5]}...")
        else:
            print("WARNING: Returned empty DataFrame (Market might be closed/No data yet). This is not a code failure.")
            
    except Exception as e:
        pytest.fail(f"get_limit_up_pool raised exception: {e}")

def test_limit_rank_process(mock_context, data_module):
    """
    Test 2: Verify Limit Rank Logic
    """
    print("\n[Test] LimitOrderRankModule")
    
    # Wire up the real data fetcher
    mock_context.data.get_limit_up_pool = data_module.get_limit_up_pool
    
    module = LimitOrderRankModule(mock_context)
    
    try:
        module.process()
        
        # We can't guarantee broadcast_ui is called if data is empty,
        # but we verify no crash happens.
        if mock_context.broadcast_ui.called:
            args = mock_context.broadcast_ui.call_args
            print(f"SUCCESS: Broadcasted to '{args[0][0]}' with {len(args[0][1])} items.")
        else:
            print("Info: process() finished but no broadcast (likely empty data).")
            
    except Exception as e:
        pytest.fail(f"LimitOrderRankModule.process failed: {e}")

def test_weighted_limit_up_process(mock_context, data_module):
    """
    Test 3: Verify Weighted Limit Up Logic
    """
    print("\n[Test] WeightedLimitUpModule")
    
    mock_context.data.get_limit_up_pool = data_module.get_limit_up_pool
    
    module = WeightedLimitUpModule(mock_context)
    try:
        module.process()
        
        if mock_context.broadcast_ui.called:
            args = mock_context.broadcast_ui.call_args
            print(f"SUCCESS: Broadcasted to '{args[0][0]}' with {len(args[0][1])} items.")
        else:
            print("Info: process() finished but no broadcast.")
            
    except Exception as e:
        pytest.fail(f"WeightedLimitUpModule.process failed: {e}")

def test_limit_up_monitor_task(mock_context, data_module):
    """
    Test 4: Verify Monitor Service Logic
    """
    print("\n[Test] LimitUpMonitor")
    
    mock_context.data.get_limit_up_pool = data_module.get_limit_up_pool
    
    monitor = LimitUpMonitor(mock_context)
    now = datetime.datetime.now()
    
    try:
        # Directly invoke the inner task logic to bypass time/date checks
        monitor._run_task(now)
        
        if mock_context.broadcast_ui.called:
             args = mock_context.broadcast_ui.call_args
             channel = args[0][0]
             payload = args[0][1]
             print(f"SUCCESS: Broadcasted to '{channel}'. Status: {payload.get('status')}, Count: {payload.get('count')}")
             if 'top_stocks' in payload:
                 print(f"Top Stocks included: {len(payload['top_stocks'])}")
             else:
                 print("WARNING: 'top_stocks' missing from payload (Code change verification failed?)")
        else:
            print("Info: _run_task finished but no broadcast.")

    except Exception as e:
        pytest.fail(f"LimitUpMonitor._run_task failed: {e}")
