import sys
import os
import yaml
import time
import logging
from threading import Event

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

# Redirect stdout/stderr to a startup log immediately for debugging VBS launch
startup_log = os.path.join(ROOT_DIR, "service_startup.log")
sys.stdout = open(startup_log, 'a', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

from vibe_core.context import Context
from vibe_core.data.factory import DataFactory
from vibe_core.driver.scheduler import SimpleScheduler
from modules.prod.limit_up_monitor import LimitUpMonitor

def load_config():
    config_path = os.path.join(ROOT_DIR, "config", "config.yaml")
    if not os.path.exists(config_path):
        # Fallback for when running not from root
        config_path = os.path.join(ROOT_DIR, "..", "config", "config.yaml")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    print(f"[{time.ctime()}] Starting VibeStock Limit Up Monitor Service...")
    print(f"CWD: {os.getcwd()}")
    
    # 1. Setup Logging
    # Ensure logs directory exists
    log_dir = os.path.join(ROOT_DIR, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(), # Still goes to startup log due to redirect
            logging.FileHandler(os.path.join(log_dir, "monitor_service.log"), encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger("MonitorService")
    
    # 2. Load Config
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    # 3. Initialize Context
    context = Context()
    
    # 4. Initialize Data Provider
    logger.info("Initializing Data Providers...")
    try:
        context.data = DataFactory.create_provider(config)
    except Exception as e:
        logger.error(f"Failed to create data provider: {e}")
        return
    
    # 5. Initialize Scheduler (Injecting SimpleScheduler)
    logger.info("Initializing Scheduler...")
    scheduler = SimpleScheduler()
    context._scheduler = scheduler
    scheduler.start()
    
    # 6. Initialize Module
    logger.info("Loading LimitUpMonitor Module...")
    monitor = LimitUpMonitor()
    monitor.initialize(context)
    
    # 7. Main Loop
    logger.info("Service Started. Running 09:20 - 15:03 daily.")
    logger.info("Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping service...")
        scheduler.stop()
        logger.info("Service stopped.")

if __name__ == "__main__":
    main()
