import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

# Import the new module directly
from modules.core.akshare_data import AkShareDataModule
from vibe_core.context import Context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestAKShare")

def test_akshare():
    print("Testing AKShare Data Module...")
    
    # Mock Context
    context = Context()
    
    try:
        # Instantiate Module
        module = AkShareDataModule(context)
        # We don't need full initialize() which registers to context.data (unless we test that)
        # But AkShareDataModule inherits AKShareAdapter, so we can call methods directly.
        print("Module created successfully.")
    except Exception as e:
        print(f"Failed to create module: {e}")
        return

    # 1. Test Snapshot
    code = "600519.SH" # Moutai
    print(f"Fetching snapshot for {code}...")
    try:
        data = module.get_snapshot([code])
        if data:
            print(f"Snapshot received: {data[0]}")
        else:
            print("Snapshot returned empty list.")
    except Exception as e:
        print(f"Snapshot failed: {e}")

    # 2. Test History
    print(f"Fetching history for {code} (2023-01-01 to 2023-01-10)...")
    try:
        df = module.get_history(code, "2023-01-01", "2023-01-10")
        if not df.empty:
            print(f"History received:\n{df.head()}")
        else:
            print("History returned empty DataFrame.")
    except Exception as e:
        print(f"History failed: {e}")

if __name__ == "__main__":
    test_akshare()
