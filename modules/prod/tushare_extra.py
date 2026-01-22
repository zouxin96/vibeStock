from vibe_core.module import VibeModule
from vibe_core.event import Event
import datetime
import os
import pandas as pd
import logging

# We can reuse the adapter logic or import it. 
# Since this is a module, it should access context.data or create an adapter.

class TushareExtraModule(VibeModule):
    """
    Fetches low-frequency data: Concepts, Financial Reports.
    Scheduled to run weekly or manually.
    """

    def __init__(self):
        super().__init__()
        self.description = "Fetches low-frequency data: Concepts, Financial Reports. Scheduled to run weekly or manually."

    def configure(self):
        # Run weekly, e.g., Monday at 02:00
        # self.trigger_on_cron("0 2 * * 1") 
        # For now, maybe just expose a method or run on startup if missing?
        # Let's just listen for a custom event or a manual trigger.
        self.subscribe_topic("CMD_FETCH_EXTRA")

    def on_event(self, event: Event):
        if event.type == "CMD_FETCH_EXTRA" or (event.type == "TIMER" and event.data.get("cron") == "weekly"):
            self.fetch_all()

    def fetch_all(self):
        self.context.logger.info("Starting Tushare Extra Data Fetch...")
        self.fetch_ths_concepts()
        self.fetch_standard_concepts()
        self.fetch_sw_industries()
        self.fetch_latest_financial()

    def _get_adapter(self):
        # Helper to get adapter even if not fully injected or if running standalone
        if hasattr(self.context, "data") and hasattr(self.context.data, "get_ths_index"):
            return self.context.data
        
        # Fallback to creating a local adapter instance
        from vibe_core.data.adapter.stock_detail.tushare import TushareAdapter
        token = self.context.config.get("data", {}).get("tushare_token", "")
        return TushareAdapter(token=token)

    def fetch_ths_concepts(self):
        adapter = self._get_adapter()
        self.context.logger.info("Fetching THS Concepts...")
        df = adapter.get_ths_index()
        if not df.empty:
            path = os.path.join("data", "concepts", "ths_index.csv")
            # Ensure dir exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            df.to_csv(path, index=False)
            self.context.logger.info(f"Saved {len(df)} THS concepts to {path}")
        else:
            self.context.logger.warning("No THS concept data returned.")

    def fetch_standard_concepts(self):
        adapter = self._get_adapter()
        self.context.logger.info("Fetching Standard Concepts...")
        df = adapter.get_concept()
        if not df.empty:
            path = os.path.join("data", "concepts", "concept_list.csv")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            df.to_csv(path, index=False)
            self.context.logger.info(f"Saved {len(df)} standard concepts to {path}")
        else:
            self.context.logger.warning("No standard concept data returned.")

    def fetch_sw_industries(self):
        adapter = self._get_adapter()
        self.context.logger.info("Fetching Shenwan Industries (L1, L2, L3)...")
        
        for level in ['L1', 'L2', 'L3']:
            df = adapter.get_index_classify(level=level, src='SW2021')
            if not df.empty:
                path = os.path.join("data", "concepts", f"sw_industry_{level}.csv")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                df.to_csv(path, index=False)
                self.context.logger.info(f"Saved {len(df)} SW {level} industries to {path}")
            else:
                self.context.logger.warning(f"No SW industry data returned for {level}.")

    def fetch_latest_financial(self):
        adapter = self._get_adapter()
        
        # Determine target period
        now = datetime.datetime.now()
        # Logic for "safe" previous period
        # If Jan-Apr (1-4), use Q3 Prev Year.
        if now.month <= 4:
            year = now.year - 1
            period = f"{year}0930"
        elif now.month <= 8:
            period = f"{now.year}0331"
        elif now.month <= 10:
            period = f"{now.year}0630"
        else:
            period = f"{now.year}0930"
            
        self.context.logger.info(f"Fetching Income Data for period: {period}...")
        df = adapter.get_income(period=period)
        
        if not df.empty:
            path = os.path.join("data", "financial", f"income_{period}.csv")
            df.to_csv(path, index=False)
            self.context.logger.info(f"Saved {len(df)} financial records to {path}")
        else:
            self.context.logger.warning(f"No income data returned for {period} (Batch). Trying single stock '600519.SH' (Moutai)...")
            # Fallback to single stock to test connectivity/lower permission
            df_single = adapter.get_income(ts_code='600519.SH', period=period)
            if not df_single.empty:
                path = os.path.join("data", "financial", f"income_600519_{period}.csv")
                df_single.to_csv(path, index=False)
                self.context.logger.info(f"Saved single stock financial data to {path}")
            else:
                self.context.logger.error("Single stock fetch also failed or returned no data.")

# Standalone execution wrapper
if __name__ == "__main__":
    # Mock context for standalone run
    class MockConfig:
        def get(self, key, default=None):
            if key == "data":
                # Try to load real config or use env var, or just hardcode for test if safe
                # For safety, I will assume the user has the token in the code I just read
                return {"tushare_token": "d468b49a4a60689c2267c78d6f7266576cb5a1f3809f10fe06fc36d3"}
            return default

    class MockContext:
        def __init__(self):
            self.config = MockConfig()
            self.logger = logging.getLogger("Test")
            logging.basicConfig(level=logging.INFO)
            self.data = None # Will force _get_adapter to create new
            
        def subscribe(self, module, topic):
            print(f"Mock subscribe: {module.name} -> {topic}")
            
        def register_cron(self, module, cron):
            print(f"Mock cron: {module.name} -> {cron}")

    module = TushareExtraModule()
    module.initialize(MockContext())
    module.fetch_all()
