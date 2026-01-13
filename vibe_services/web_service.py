from vibe_core.service import IService
import threading
import uvicorn
from vibe_server.server import app

class WebServerService(IService):
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.name_ = "web_server"
        self._thread = None
        self._server = None # Uvicorn server instance control is tricky without custom subclass

    @property
    def name(self) -> str:
        return self.name_

    def start(self):
        # Run Uvicorn in a separate thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        # Note: uvicorn.run is blocking. 
        # For programmatic shutdown, we ideally need uvicorn.Server but .run is simpler for prototype
        uvicorn.run(app, host=self.host, port=self.port, log_level="warning")

    def stop(self):
        # Hard to stop uvicorn.run directly without access to Server object.
        # For this prototype, we rely on daemon thread being killed when main process exits.
        pass
