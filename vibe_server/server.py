from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
import json
import csv
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

# --- Data View APIs ---

@app.get("/api/data/files")
async def list_data_files():
    """List available data files."""
    data_dir = os.path.join(os.getcwd(), "data", "daily")
    if not os.path.exists(data_dir):
        return []
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    files.sort(reverse=True) # Newest first
    return files

@app.get("/api/data/content")
async def get_data_content(file: str):
    """Get content of a CSV file (top 100 lines)."""
    file_path = os.path.join(os.getcwd(), "data", "daily", file)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    content = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if headers:
                content.append(headers)
                for i, row in enumerate(reader):
                    if i >= 100: break
                    content.append(row)
        return {"filename": file, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/sources")
async def list_data_sources():
    """Return status of data sources."""
    sources = []
    data_dir = os.path.join(os.getcwd(), "data", "daily")
    
    # 1. Tushare Stats
    ts_files = []
    if os.path.exists(data_dir):
        ts_files = [f for f in os.listdir(data_dir) if f.startswith("daily_") and f.endswith(".csv")]
    
    # Estimate count from latest file if exists
    ts_count = 0
    ts_last_sync = "Never"
    if ts_files:
        ts_files.sort(reverse=True)
        latest = ts_files[0]
        ts_last_sync = latest.replace("daily_", "").replace(".csv", "") # YYYYMMDD
        # Formatting to YYYY-MM-DD
        if len(ts_last_sync) == 8:
            ts_last_sync = f"{ts_last_sync[:4]}-{ts_last_sync[4:6]}-{ts_last_sync[6:]}"
        
        # Read line count of latest file
        try:
            with open(os.path.join(data_dir, latest), 'r', encoding='utf-8') as f:
                ts_count = sum(1 for _ in f) - 1 # Exclude header
        except:
            ts_count = -1
            
    sources.append({
        "id": "tushare",
        "name": "Tushare Pro",
        "count": max(0, ts_count),
        "last_sync": ts_last_sync,
        "files_count": len(ts_files)
    })

    # 2. AKShare Stats
    ak_files = []
    if os.path.exists(data_dir):
        ak_files = [f for f in os.listdir(data_dir) if f.startswith("akshare_") and f.endswith(".csv")]
        
    ak_count = 0
    ak_last_sync = "Never"
    if ak_files:
        ak_files.sort(reverse=True)
        latest = ak_files[0]
        ak_last_sync = latest.replace("akshare_", "").replace(".csv", "")
        if len(ak_last_sync) == 8:
            ak_last_sync = f"{ak_last_sync[:4]}-{ak_last_sync[4:6]}-{ak_last_sync[6:]}"
            
        try:
            with open(os.path.join(data_dir, latest), 'r', encoding='utf-8') as f:
                ak_count = sum(1 for _ in f) - 1
        except:
            ak_count = -1

    sources.append({
        "id": "akshare",
        "name": "AKShare (Open Source)",
        "count": max(0, ak_count),
        "last_sync": ak_last_sync,
        "files_count": len(ak_files)
    })

    return sources

def _run_manual_sync(source: str):
    """Run sync in background."""
    print(f"Starting sync for {source}...")
    try:
        if source == "tushare":
            # Load config to get token
            config_path = os.path.join("config", "config.yaml")
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            token = config.get("data", {}).get("tushare_token", "")
            
            from vibe_data.adapter.tushare_adapter import TushareAdapter
            adapter = TushareAdapter(token=token)
            adapter.sync_daily_data()
            
        elif source == "akshare":
            from vibe_data.adapter.akshare_adapter import AKShareAdapter
            adapter = AKShareAdapter()
            adapter.sync_daily_data()
            
        print(f"Manual sync for {source} completed.")
    except Exception as e:
        print(f"Manual sync for {source} failed: {e}")

@app.post("/api/data/sync")
async def trigger_sync(background_tasks: BackgroundTasks, source: str = "tushare"):
    """Trigger a manual data sync."""
    background_tasks.add_task(_run_manual_sync, source)
    return {"status": "started", "message": f"Sync for {source} started in background"}


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
