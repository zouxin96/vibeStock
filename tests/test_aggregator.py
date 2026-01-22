import unittest
import threading
import time
import pandas as pd
from typing import List, Optional
from vibe_core.data.provider import IDataProvider, DataDimension, SyncPolicy
from vibe_core.data.aggregator import DataAggregator

class MockProvider(IDataProvider):
    def __init__(self):
        self.call_count = 0
        self.full_call_count = 0
        self.lock = threading.Lock()
        
    @property
    def data_dimension(self):
        return DataDimension.OTHER
    
    @property
    def sync_policy(self):
        return SyncPolicy.MANUAL
        
    @property
    def archive_filename_template(self):
        return "mock_{date}.csv"
        
    def get_price(self, code, date):
        with self.lock:
            self.call_count += 1
        time.sleep(0.1) # Simulate network delay
        return 100.0

    def get_history(self, code, start, end):
        with self.lock:
            self.call_count += 1
        time.sleep(0.1)
        return pd.DataFrame()
        
    def get_snapshot(self, codes: List[str]):
        # This shouldn't be called if get_full_snapshot is prioritized by Aggregator logic for AKShare
        # But Aggregator only uses full_snapshot if a specific flag/check is met.
        # In our aggregator implementation, we checked: 
        # `if hasattr(self._provider, 'get_full_snapshot'):`
        with self.lock:
            self.call_count += 1
        time.sleep(0.1)
        return [{"code": c, "price": 100.0} for c in codes]

    def get_full_snapshot(self) -> pd.DataFrame:
        with self.lock:
            self.full_call_count += 1
        time.sleep(0.2) # Simulate slower full fetch
        # Return a dummy dataframe simulating full market
        data = {
            "代码": ["000001", "000002", "600000", "600519"],
            "名称": ["平安", "万科", "浦发", "茅台"],
            "最新价": [10.0, 15.0, 20.0, 1800.0],
            "涨跌幅": [1.0, 2.0, 0.5, -0.5],
            "今开": [9.0, 14.0, 19.0, 1810.0],
            "最高": [11.0, 16.0, 21.0, 1820.0],
            "最低": [9.0, 14.0, 19.0, 1790.0],
            "成交量": [1000, 2000, 3000, 500]
        }
        return pd.DataFrame(data)

    def get_table(self, table, date=None):
        with self.lock:
            self.call_count += 1
        return pd.DataFrame()

class TestDataAggregator(unittest.TestCase):
    def setUp(self):
        self.mock_provider = MockProvider()
        self.aggregator = DataAggregator(self.mock_provider, cache_ttl=1.0)
        
    def test_single_flight_get_price(self):
        """Test that concurrent requests for same price result in single provider call"""
        def task():
            self.aggregator.get_price("000001", "20230101")
            
        threads = [threading.Thread(target=task) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        # Should be 1 call because they overlap
        self.assertEqual(self.mock_provider.call_count, 1)
        
    def test_cache_ttl(self):
        """Test that cache expires"""
        self.aggregator.get_price("000001", "20230101")
        self.assertEqual(self.mock_provider.call_count, 1)
        
        # Immediate retry -> cached
        self.aggregator.get_price("000001", "20230101")
        self.assertEqual(self.mock_provider.call_count, 1)
        
        # Wait for TTL
        time.sleep(1.1)
        
        # Retry -> new call
        self.aggregator.get_price("000001", "20230101")
        self.assertEqual(self.mock_provider.call_count, 2)

    def test_full_snapshot_aggregation(self):
        """
        Test that get_snapshot calls get_full_snapshot on the provider
        and filters correctly, sharing the full data fetch.
        """
        # Module A wants 000001
        # Module B wants 600519
        # Both should trigger ONE full fetch and return correct subsets.
        
        results = {}
        
        def task_a():
            res = self.aggregator.get_snapshot(["000001"])
            results['a'] = res
            
        def task_b():
            res = self.aggregator.get_snapshot(["600519"])
            results['b'] = res
            
        t1 = threading.Thread(target=task_a)
        t2 = threading.Thread(target=task_b)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # Verify only one full fetch happened
        self.assertEqual(self.mock_provider.full_call_count, 1)
        
        # Verify results
        self.assertEqual(len(results['a']), 1)
        self.assertEqual(results['a'][0]['code'], "000001")
        self.assertEqual(results['a'][0]['price'], 10.0)
        
        self.assertEqual(len(results['b']), 1)
        self.assertEqual(results['b'][0]['code'], "600519")
        self.assertEqual(results['b'][0]['price'], 1800.0)

if __name__ == '__main__':
    unittest.main()
