import sys
import os
import logging

# Setup basic logging
logging.basicConfig(level=logging.DEBUG)

# Add project root to path
sys.path.append(os.getcwd())

from vibe_data.adapter.sina_adapter import SinaLiveAdapter

def test_sina():
    adapter = SinaLiveAdapter()
    codes = ["sh000001", "sh600519"]
    print(f"Testing Sina Adapter with codes: {codes}")
    
    try:
        data = adapter.get_snapshot(codes)
        print(f"Returned {len(data)} results.")
        for item in data:
            print(item)
            
        if not data:
            print("FAILED: No data returned.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_sina()
