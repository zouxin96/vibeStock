import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

from vibe_data.factory import DataFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestAKShare")

def test_akshare():
    print("Testing AKShare Adapter...")
    
    # Mock config
    config = {
        "data": {
            "provider": "akshare"
        }
    }
    
    try:
        adapter = DataFactory.create_provider(config)
        print("Adapter created successfully.")
    except Exception as e:
        print(f"Failed to create adapter: {e}")
        return

    # 1. Test Snapshot
    code = "600519.SH" # Moutai
    print(f"Fetching snapshot for {code}...")
    try:
        data = adapter.get_snapshot([code])
        if data:
            print(f"Snapshot received: {data[0]}")
        else:
            print("Snapshot returned empty list.")
    except Exception as e:
        print(f"Snapshot failed: {e}")

    # 2. Test History
    print(f"Fetching history for {code} (2023-01-01 to 2023-01-10)...")
    try:
        df = adapter.get_history(code, "2023-01-01", "2023-01-10")
        if not df.empty:
            print(f"History received:\n{df.head()}")
        else:
            print("History returned empty DataFrame.")
    except Exception as e:
        print(f"History failed: {e}")

if __name__ == "__main__":
    test_akshare()
