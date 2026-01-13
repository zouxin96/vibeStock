import time
import threading
from typing import List, Tuple, Callable, Optional

class SimpleScheduler:
    """
    A very basic scheduler to replace APScheduler for zero-dependency.
    Supports tagging jobs for cancellation.
    """
    def __init__(self):
        # Job structure: (interval, function, tag, thread_handle)
        self.jobs: List[Tuple[float, Callable, Optional[str], threading.Thread]] = []
        self.running = False
        self._lock = threading.Lock()

    def add_interval_job(self, func: Callable, interval_seconds: int, tag: str = None):
        """
        Add a job that runs every X seconds.
        :param tag: Optional string tag (usually module name) to group jobs.
        """
        def loop():
            while self.running:
                # Check if this specific job instance is still in the valid jobs list
                # This is a bit hacky for a simple scheduler but effective for stopping threads
                if not self._is_job_valid(tag, func):
                    break
                
                try:
                    func()
                except Exception as e:
                    print(f"Scheduler Job Error ({tag}): {e}")
                    
                time.sleep(interval_seconds)
        
        t = threading.Thread(target=loop, daemon=True)
        
        with self._lock:
            self.jobs.append((interval_seconds, func, tag, t))
            if self.running:
                t.start()

    def _is_job_valid(self, tag, func):
        """Check if the job is still in the active list (hasn't been cancelled)"""
        with self._lock:
            for _, f, t, _ in self.jobs:
                if f == func and t == tag:
                    return True
        return False

    def cancel_jobs(self, tag: str):
        """
        Remove all jobs with the given tag.
        The threads will exit on their next loop iteration because _is_job_valid will return False.
        """
        with self._lock:
            original_count = len(self.jobs)
            self.jobs = [job for job in self.jobs if job[2] != tag]
            removed_count = original_count - len(self.jobs)
            if removed_count > 0:
                print(f"[Scheduler] Cancelled {removed_count} jobs for tag: {tag}")

    def start(self):
        self.running = True
        with self._lock:
            for _, _, _, t in self.jobs:
                if not t.is_alive():
                    t.start()

    def stop(self):
        self.running = False
