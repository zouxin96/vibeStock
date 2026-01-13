import sys
import os
import logging
import time
import shutil

# Add project root to path
sys.path.append(os.getcwd())

from vibe_core.context import Context
from vibe_core.storage import CSVStorageService

# Mocking Logger
logging.basicConfig(level=logging.INFO)

def test_storage_service():
    print("Testing CSVStorageService...")
    
    # 1. Initialize Context (which initializes Storage)
    context = Context()
    
    if not hasattr(context, "storage"):
        print("FAIL: Context.storage not initialized.")
        return

    print("Context.storage initialized.")

    # 2. Test save_record
    category = "test_category"
    record = {"id": 1, "name": "Item 1", "price": 10.5}
    
    print(f"Saving record to category '{category}'...")
    context.storage.save_record(category, record)
    
    # Verify file existence
    import datetime
    today = datetime.datetime.now().strftime("%Y%m%d")
    expected_path = os.path.join("data", "storage", category, f"{today}.csv")
    
    if os.path.exists(expected_path):
        print(f"SUCCESS: File created at {expected_path}")
        
        # Verify content
        with open(expected_path, 'r') as f:
            content = f.read()
            print(f"File Content:\n{content}")
            if "Item 1" in content:
                print("Content verification passed.")
            else:
                print("FAIL: Content verification failed.")
    else:
        print(f"FAIL: File not found at {expected_path}")

    # Clean up
    # shutil.rmtree(os.path.join("data", "storage", category))
    print("Test finished.")

if __name__ == "__main__":
    test_storage_service()
