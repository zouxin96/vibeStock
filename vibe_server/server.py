from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
import json
from typing import List, Dict

from .websocket_manager import manager

app = FastAPI()

# Mount static files
static_dir = os.path.join(os.getcwd(), "ui")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def get():
    with open(os.path.join(static_dir, "index.html"), 'r', encoding='utf-8') as f:
        return HTMLResponse(content=f.read())

@app.get("/api/status")
async def get_status():
    """Return the last update time of widgets to check data health."""
    return JSONResponse(manager.last_updates)

@app.get("/api/layout")
async def get_layout():
    """Load dashboard layout."""
    layout_path = os.path.join("config", "dashboard_layout.json")
    if os.path.exists(layout_path):
        try:
            with open(layout_path, 'r', encoding='utf-8') as f:
                return JSONResponse(json.load(f))
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse([]) # Empty list means default layout

@app.post("/api/layout")
async def save_layout(layout: List[Dict] = Body(...)):
    """Save dashboard layout."""
    layout_path = os.path.join("config", "dashboard_layout.json")
    try:
        with open(layout_path, 'w', encoding='utf-8') as f:
            json.dump(layout, f, indent=2)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open and listen for client messages (e.g. ping)
            data = await websocket.receive_text()
            # We can handle client commands here if needed
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
