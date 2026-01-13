from typing import List, Dict
from .crawler import BaseCrawler
from .analyzer import BaseAnalyzer

class ContentPipeline:
    def __init__(self, crawler: BaseCrawler, analyzer: BaseAnalyzer):
        self.crawler = crawler
        self.analyzer = analyzer

    def run(self):
        print(f"Starting pipeline with {self.crawler.__class__.__name__}")
        raw_items = self.crawler.crawl()
        print(f"Crawled {len(raw_items)} items.")
        
        results = []
        for item in raw_items:
            # 1. Archive
            path = self.crawler.save_raw(item)
            print(f"Saved raw to {path}")
            
            # 2. Analyze
            signal = self.analyzer.analyze(item)
            results.append(signal)
            
            # 3. In a real app, we would publish this signal to EventBus
            print(f"Generated Signal: {signal}")
            
        return results
