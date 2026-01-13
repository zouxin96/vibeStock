from vibe_core.service import IService
from vibe_driver.scheduler import SimpleScheduler
import threading

class SchedulerService(IService):
    def __init__(self):
        self._scheduler = SimpleScheduler()
        self._name = "scheduler"

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def scheduler(self) -> SimpleScheduler:
        return self._scheduler

    def start(self):
        # SimpleScheduler uses internal threads, so we just call start
        self._scheduler.start()

    def stop(self):
        self._scheduler.stop()
