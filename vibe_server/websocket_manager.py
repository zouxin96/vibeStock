from typing import List, Dict, Any
import json
import asyncio
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_updates: Dict[str, str] = {} # Track last update time for widgets

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
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
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message))
        except RuntimeError:
            # If no loop is running (e.g. testing), just print
            print(f"Mock Broadcast: {message}")

# Singleton instance
manager = WebSocketManager()
