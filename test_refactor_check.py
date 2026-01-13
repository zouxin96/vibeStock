import sys
import os
import logging

# Add current dir to path
sys.path.append(os.getcwd())

try:
    from vibe_data.provider import FetcherType, DataCategory, BaseFetcher
    from vibe_data.adapter.tushare_adapter import TushareAdapter
    from vibe_data.adapter.sina_adapter import SinaLiveAdapter
    
    print("Imports successful.")
    
    # Test BaseFetcher logging logic
    class TestFetcher(BaseFetcher):
        def __init__(self, f_type):
            super().__init__(f_type)
            
    # Mock logger
    logging.basicConfig(level=logging.DEBUG)
    
    realtime = TestFetcher(FetcherType.REALTIME)
    print(f"Realtime fetcher type: {realtime.fetcher_type}")
    
    postmarket = TestFetcher(FetcherType.POST_MARKET)
    print(f"PostMarket fetcher type: {postmarket.fetcher_type}")
    
    # Test path generation
    path_pm = postmarket.get_save_path(DataCategory.STOCK, "test.csv")
    print(f"PostMarket Path: {path_pm}")
    
    path_rt = realtime.get_save_path(DataCategory.STOCK, "test.csv")
    print(f"Realtime Path: {path_rt}")
    
    print("Verification complete.")
except Exception as e:
    print(f"Verification failed: {e}")
    import traceback
    traceback.print_exc()
