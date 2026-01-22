import os
import sys
import threading
import time
import yaml
import logging
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

# Fix for PyInstaller & akshare data paths
if getattr(sys, 'frozen', False):
    # If running as exe, we are in a temp folder.
    # Ensure cwd is set to the exe location for config reading, 
    # BUT we need to be careful not to break internal relative imports.
    # Actually, config is in ROOT_DIR which we derive from executable path below.
    pass

# Ensure we can find the project modules
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    ROOT_DIR = os.path.dirname(sys.executable)
    # The internal _MEI folder is in sys._MEIPASS
    sys.path.append(sys._MEIPASS)
else:
    # Running as script
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(ROOT_DIR)

# Setup logging
LOG_DIR = os.path.join(ROOT_DIR, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

# Redirect stderr to file to catch startup crashes
sys.stderr = open(os.path.join(LOG_DIR, "tray_error.log"), "a", encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "tray_monitor.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TrayApp")

# --- Import Guard for Akshare ---
# Akshare requires data files that might be missing in frozen builds.
# We accept this risk but log it.
try:
    import akshare as ak
except Exception as e:
    logger.error(f"Failed to import akshare: {e}")
    # We continue, assuming the data provider might handle the missing akshare gracefully 
    # (our updated limit_up_monitor does handle ak=None)

from vibe_core.context import Context
from vibe_core.data.factory import DataFactory
from vibe_core.driver.scheduler import SimpleScheduler
from modules.prod.limit_up_monitor import LimitUpMonitor
from modules.core.akshare_data import AkShareDataModule

# Setup logging
LOG_DIR = os.path.join(ROOT_DIR, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "tray_monitor.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TrayApp")

class MonitorService:
    def __init__(self):
        self.context = None
        self.scheduler = None
        self.monitor = None
        self.running = False
        self.status_text = "Initializing..."
        self._load()

    def _load(self):
        try:
            config_path = os.path.join(ROOT_DIR, "config", "config.yaml")
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            
            self.context = Context()
            self.context.data = DataFactory.create_provider(self.config)
            
            # Use SimpleScheduler
            self.scheduler = SimpleScheduler()
            self.context._scheduler = self.scheduler
            
            # Init Dependencies
            try:
                self.ak_module = AkShareDataModule()
                self.ak_module.initialize(self.context)
                logger.info("AkShareDataModule initialized")
            except Exception as e:
                logger.error(f"Failed to init AkShareDataModule: {e}")

            # Init Monitor
            self.monitor = LimitUpMonitor()
            self.monitor.initialize(self.context)
            
            self.status_text = "Ready"
        except Exception as e:
            logger.error(f"Init failed: {e}")
            self.status_text = f"Init Error: {str(e)[:20]}"

    def start(self):
        if not self.running and self.scheduler:
            try:
                self.scheduler.start()
                self.running = True
                self.status_text = "Running (09:20-15:30)"
                logger.info("Service started")
            except Exception as e:
                logger.error(f"Start failed: {e}")

    def stop(self):
        if self.running and self.scheduler:
            try:
                self.scheduler.stop()
                # SimpleScheduler needs to be re-instantiated to restart usually, 
                # but let's see if we can pause. 
                # Our SimpleScheduler implementation breaks the loop on stop().
                # So to restart, we technically need a new scheduler instance or reset the flag.
                # Let's re-create scheduler for safety.
                self.scheduler = SimpleScheduler()
                self.context._scheduler = self.scheduler
                # Re-register cron
                self.monitor.context = self.context
                self.monitor.configure()
                
                self.running = False
                self.status_text = "Stopped"
                logger.info("Service stopped")
            except Exception as e:
                logger.error(f"Stop failed: {e}")

def create_icon(color):
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 4, height // 4, 3 * width // 4, 3 * height // 4),
        fill='white')
    return image

service = MonitorService()

def on_start(icon, item):
    service.start()
    icon.icon = create_icon('green')
    icon.notify("VibeStock Monitor Started", "Service Running")

def on_stop(icon, item):
    service.stop()
    icon.icon = create_icon('red')
    icon.notify("VibeStock Monitor Stopped", "Service Stopped")

def on_status(icon, item):
    icon.notify(f"Status: {service.status_text}", "VibeStock Monitor")

def on_exit(icon, item):
    service.stop()
    icon.stop()

def run_tray():
    # Start service automatically on launch
    service.start()
    
    icon_image = create_icon('green')
    
    menu = pystray.Menu(
        item('Start Service', on_start, enabled=lambda i: not service.running),
        item('Stop Service', on_stop, enabled=lambda i: service.running),
        item('Check Status', on_status),
        pystray.Menu.SEPARATOR,
        item('Exit', on_exit)
    )

    icon = pystray.Icon("VibeStock", icon_image, "VibeStock Monitor", menu)
    icon.run()

if __name__ == "__main__":
    try:
        run_tray()
    except Exception as e:
        logger.critical(f"Tray App Crashed: {e}", exc_info=True)
