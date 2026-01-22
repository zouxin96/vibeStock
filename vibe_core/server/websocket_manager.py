from typing import List, Dict, Any, Callable, Awaitable
import json
import asyncio
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_updates: Dict[str, str] = {} # Track last update time for widgets
        self.loop = None
        self.on_message_handler: Callable[[Dict[str, Any]], Awaitable[None]] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        print(f"[WS] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WS] Client disconnected. Total: {len(self.active_connections)}")

    def set_handler(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Set the handler for incoming client messages."""
        self.on_message_handler = handler

    async def handle_message(self, websocket: WebSocket, message_text: str):
        """Process incoming raw message text."""
        if self.on_message_handler:
            try:
                data = json.loads(message_text)
                await self.on_message_handler(data)
            except json.JSONDecodeError:
                print(f"[WS] Invalid JSON received: {message_text}")
            except Exception as e:
                print(f"[WS] Error handling message: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected clients.
        """
        # Track update time
        if message.get("type") == "update" and "widget_id" in message:
            import datetime
            self.last_updates[message["widget_id"]] = datetime.datetime.now().isoformat()

        payload = json.dumps(message)
        # Create a copy of the list to iterate over, in case disconnect modifies it concurrently
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception as e:
                print(f"[WS] Error sending to client: {e}")
                # We typically rely on the receive loop to detect disconnects, 
                # but send failure is also a sign.
                
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
            pass

# Singleton instance
manager = WebSocketManager()