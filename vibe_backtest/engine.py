import datetime
from typing import List, Any
from vibe_core.context import Context
from vibe_core.event import Event
from vibe_core.module import VibeModule
from vibe_data.factory import DataFactory

class BacktestContext(Context):
    def __init__(self, start_time: datetime.datetime, end_time: datetime.datetime):
        super().__init__()
        self._current_time = start_time
        self.start_time = start_time
        self.end_time = end_time
        self.data = DataFactory.create_provider({"system": {"mode": "backtest"}})
        self.output_log: List[str] = []

    @property
    def now(self):
        return self._current_time

    def set_time(self, dt: datetime.datetime):
        self._current_time = dt

    def register_cron(self, module, cron_expr):
        # In backtest, we might ignore complex crons or approximate them
        pass

class BacktestEngine:
    def __init__(self, modules: List[VibeModule], start_str: str, end_str: str):
        self.modules = modules
        self.start = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        self.end = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M")
        self.ctx = BacktestContext(self.start, self.end)

    def run(self):
        print(f"Starting Backtest from {self.start} to {self.end}")
        
        # Initialize modules
        for mod in self.modules:
            mod.initialize(self.ctx)
            print(f"Initialized {mod.name}")

        # Time Loop (e.g., 1 minute step)
        curr = self.start
        step = datetime.timedelta(minutes=1)
        
        while curr <= self.end:
            self.ctx.set_time(curr)
            
            # 1. Generate Quote Event (Simulated)
            # In a real impl, we would read from self.ctx.data.get_price(curr)
            # Here we just emit a generic TICK event
            evt = Event(event_type="QUOTE", topic="market.tick", timestamp=curr.timestamp())
            
            # 2. Dispatch to modules
            for mod in self.modules:
                mod.on_event(evt)
            
            curr += step
            
        print("Backtest Complete.")
