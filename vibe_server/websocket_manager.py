from typing import List, Dict, Any
import json
import asyncio
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_updates: Dict[str, str] = {} # Track last update time for widgets
        self.loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        if self.loop is None:
            self.loop = asyncio.get_running_loop()
        print(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print("Client disconnected.")

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected clients.
        """
        # Track update time
        if message.get("type") == "update" and "widget_id" in message:
            import datetime
            self.last_updates[message["widget_id"]] = datetime.datetime.now().isoformat()

        payload = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                print(f"Error sending to client: {e}")
                # Potentially remove dead connection here
                
    def broadcast_sync(self, message: Dict[str, Any]):
        """
        Helper to run broadcast from synchronous code (used by Context).
        This schedules the async broadcast task on the running event loop.
        """
        try:
            # 1. Try to use the captured loop (thread-safe way)
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)
                return

            # 2. Try current loop (if we are in async context)
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message))
            
        except RuntimeError:
            # If no loop is running (e.g. testing or startup), just print
            # Only print if we actually have connections, otherwise it's just noise during startup
            if self.active_connections:
                print(f"Mock Broadcast (Connections active but no loop found?): {message}")
            else:
                pass # Silent drop if no one listening

# Singleton instance
manager = WebSocketManager()
