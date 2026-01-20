import os
import datetime
import traceback

LOG_FILE = "debug_data_fetch.log"

def log_debug(msg):
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass

def log_error(msg, e):
    log_debug(f"ERROR: {msg} - {str(e)}")
    log_debug(traceback.format_exc())
