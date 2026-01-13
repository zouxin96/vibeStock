import sys
import os
import logging
from vibe_data.factory import DataFactory
from vibe_data.provider import DataCategory

# Add current dir to path
sys.path.append(os.getcwd())

try:
    print("Testing TushareInfoAdapter...")
    
    # Mock config
    config = {
        "data": {
            "provider": "tushare_info",
            "tushare_token": "TEST_TOKEN" # Won't actually fetch but tests init
        }
    }
    
    adapter = DataFactory.create_provider(config)
    print(f"Adapter created: {type(adapter).__name__}")
    
    path = adapter.get_save_path(DataCategory.INFO, "test_info.csv")
    print(f"Save path: {path}")
    
    print("Verification complete.")
except Exception as e:
    print(f"Verification failed: {e}")
    import traceback
    traceback.print_exc()
