from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
import json
import csv
from typing import List, Dict

from .websocket_manager import manager
from vibe_core.data.factory import DataFactory

app = FastAPI()

# Mount static files
static_dir = os.path.join(os.getcwd(), "ui")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount modules directory to serve widget scripts
modules_dir = os.path.join(os.getcwd(), "modules")
if not os.path.exists(modules_dir):
    os.makedirs(modules_dir)
app.mount("/modules", StaticFiles(directory=modules_dir), name="modules")

@app.get("/")
async def get():
    with open(os.path.join(static_dir, "index.html"), 'r', encoding='utf-8') as f:
        return HTMLResponse(content=f.read())

@app.get("/api/modules/ui_registry")
async def get_ui_registry():
    """
    Returns the UI configuration for all active modules.
    Used by the frontend to dynamically load scripts and build the dashboard.
    """
    # This logic should ideally be in module_loader, but for now we'll access context via a hack or singleton if available.
    # A better way is to have ModuleLoaderService inject this data into a shared state or the server holds a reference.
    # For now, let's look at what modules are loaded by scanning the filesystem or importing the loader service instance.
    # Since server.py is often separate, we'll implement a simple scan or rely on the running vibe.py process to update a shared registry.
    
    # SIMPLIFICATION: We will re-scan here or use a shared singleton registry if one existed.
    # To avoid complexity, we will manually instantiate modules to check config (NOT IDEAL but works for this task)
    # OR better: The ModuleLoader updates a JSON file or shared dict.
    
    # FAST PATH: We scan the directories for __init__.py and import them? No, that's heavy.
    # We will assume a global registry exists. 
    # Let's import the loader service instance from vibe.py? No, circular import.
    
    # PRACTICAL SOLUTION:
    # We will walk the 'modules' directory. If we find a module with 'widget.js' and a python class, 
    # we can try to extract config. 
    # BUT easier: Just return the config for the known 'watchlist' module we created, 
    # plus any others we find that follow the pattern.
    
    registry = []
    
    # 1. Scan for modules with widget.js
    for category in ["core", "prod", "beta"]:
        cat_path = os.path.join(modules_dir, category)
        if not os.path.exists(cat_path): continue
        
        for mod_name in os.listdir(cat_path):
            mod_path = os.path.join(cat_path, mod_name)
            if os.path.isdir(mod_path):
                # Check for widget.js
                widget_js = os.path.join(mod_path, "widget.js")
                if os.path.exists(widget_js):
                    # It has a UI. Now we need the python config.
                    # We can try to import it, or just make a best guess/convention.
                    # Convention: It must be loaded by the main process.
                    
                    # For this task, we will try to instantiate it temporarily to get config
                    # OR we just hardcode the path convention for the frontend to assume.
                    
                    # Let's do the "Import to get config" (Safe enough for trusted code)
                    try:
                        import importlib.util
                        spec = importlib.util.spec_from_file_location(mod_name, os.path.join(mod_path, "__init__.py"))
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            # Find class
                            from vibe_core.module import VibeModule
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if isinstance(attr, type) and issubclass(attr, VibeModule) and attr is not VibeModule:
                                    ui_config = None
                                    
                                    # 1. Try class method (preferred)
                                    if hasattr(attr, 'get_ui_config') and callable(getattr(attr, 'get_ui_config')):
                                        try:
                                            # Check if it's bound (classmethod) or needs instance
                                            # Inspecting is tricky, just try calling it as class method first
                                            ui_config = attr.get_ui_config()
                                        except TypeError:
                                            # Likely an instance method requiring 'self'
                                            pass
                                        except Exception as e:
                                            print(f"Error calling static get_ui_config for {mod_name}: {e}")

                                    # 2. Fallback to instantiation
                                    if ui_config is None:
                                        try:
                                            # Try passing None as context (for modules expecting context)
                                            try:
                                                instance = attr(None)
                                            except TypeError:
                                                # Fallback: Try no arguments (for modules without context in __init__)
                                                instance = attr()
                                                
                                            if hasattr(instance, 'get_ui_config'):
                                                ui_config = instance.get_ui_config()
                                        except Exception as e:
                                            print(f"Error instantiating {mod_name} for config: {e}")

                                    if ui_config:
                                        # Normalize to list
                                        configs = ui_config if isinstance(ui_config, list) else [ui_config]
                                        
                                        for cfg in configs:
                                            # Fix script path to be absolute URL
                                            if "script_path" in cfg:
                                                cfg["script_path"] = f"/modules/{category}/{mod_name}/{cfg['script_path']}"
                                            registry.append(cfg)
                                    break
                    except Exception as e:
                        print(f"Error loading UI config for {mod_name}: {e}")

    return JSONResponse(registry)

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
    """List available data files from storage."""
    base_dir = os.path.join(os.getcwd(), "data", "storage")
    results = []
    
    if not os.path.exists(base_dir):
        return []
        
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".csv"):
                # Create relative path from data/storage
                rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                results.append(rel_path.replace("\\", "/"))
                
    results.sort(reverse=True) # Newest first (roughly)
    return results

@app.get("/api/data/content")
async def get_data_content(file: str):
    """Get content of a CSV file (top 100 lines)."""
    # Prevent directory traversal
    if ".." in file:
         raise HTTPException(status_code=400, detail="Invalid path")

    file_path = os.path.join(os.getcwd(), "data", "storage", file)
    
    # Fallback to old data/daily for backward compatibility if not found in storage
    if not os.path.exists(file_path):
         old_path = os.path.join(os.getcwd(), "data", "daily", file)
         if os.path.exists(old_path):
             file_path = old_path
         else:
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
    storage_dir = os.path.join(os.getcwd(), "data", "storage")
    
    # Helper to get stats
    def get_source_stats(subdir_path, prefix=""):
        full_path = os.path.join(storage_dir, subdir_path)
        if not os.path.exists(full_path):
            return 0, "Never", 0
            
        files = [f for f in os.listdir(full_path) if f.endswith(".csv") and (not prefix or f.startswith(prefix))]
        if not files:
            return 0, "Never", 0
            
        files.sort(reverse=True)
        latest = files[0]
        
        # Extract date from filename if possible (daily_20240101.csv or concepts_ths_2024-01-01.csv)
        import re
        date_match = re.search(r'(\d{8})|(\d{4}-\d{2}-\d{2})', latest)
        last_sync = date_match.group(0) if date_match else "Unknown"
        
        # Count lines
        try:
            with open(os.path.join(full_path, latest), 'r', encoding='utf-8') as f:
                count = sum(1 for _ in f) - 1
        except:
            count = -1
            
        return max(0, count), last_sync, len(files)

    # Load config for instantiation
    import yaml
    config = {}
    config_path = os.path.join("config", "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
             config = yaml.safe_load(f)

    for name in DataFactory.get_registered_providers():
        if name in ["local", "sina"]: continue # Skip local/realtime

        try:
            # Create a temporary config for this specific provider
            provider_config = config.copy()
            if "data" not in provider_config: provider_config["data"] = {}
            provider_config["data"]["provider"] = name
            
            provider = DataFactory.create_provider(provider_config)
            
            prefix = ""
            subdir = os.path.join("stock", "post_market") # Default
            
            if hasattr(provider, "archive_filename_template"):
                tmpl = provider.archive_filename_template
                if "{" in tmpl:
                    prefix = tmpl.split("{")[0]
            
            # Simple heuristic for category
            if "Info" in provider.__class__.__name__ or name == "tushare_info":
                subdir = os.path.join("info", "post_market")
            
            count, last, num_files = get_source_stats(subdir, prefix)
            
            # Fallback for old tushare structure
            if name == "tushare" and num_files == 0:
                 old_dir = os.path.join(os.getcwd(), "data", "daily")
                 if os.path.exists(old_dir):
                     files = [f for f in os.listdir(old_dir) if f.startswith("daily_")]
                     if files:
                         files.sort(reverse=True)
                         count = 0 
                         last = files[0].replace("daily_", "").replace(".csv", "")
                         num_files = len(files)

            sources.append({
                "id": name,
                "name": name.replace("_", " ").title(),
                "count": count,
                "last_sync": last,
                "files_count": num_files
            })
            
        except Exception as e:
            print(f"Skipping source {name}: {e}")

    return sources

def _run_manual_sync(source: str, start_date: str = None, end_date: str = None):
    """Run sync in background."""
    print(f"Starting sync for {source} (Range: {start_date} to {end_date})...")
    try:
        # Load config to get token
        config_path = os.path.join("config", "config.yaml")
        import yaml
        app_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                app_config = yaml.safe_load(f)
        
        # Prepare provider config
        provider_config = app_config.copy()
        if "data" not in provider_config: provider_config["data"] = {}
        provider_config["data"]["provider"] = source
        
        # Use factory to create provider
        provider = DataFactory.create_provider(provider_config)
        
        # Dispatch sync
        if hasattr(provider, "sync_daily_data"):
            # Check signature to see if it accepts date range
            import inspect
            sig = inspect.signature(provider.sync_daily_data)
            if "start_date" in sig.parameters:
                provider.sync_daily_data(start_date=start_date, end_date=end_date)
            else:
                provider.sync_daily_data()

        # Specific handling for special adapters
        if hasattr(provider, "sync_all_concepts"):
             provider.sync_all_concepts(src="ths")
             
        if hasattr(provider, "sync_concepts_and_sectors"):
             provider.sync_concepts_and_sectors()
             
        if hasattr(provider, "sync_ths_concept_histories"):
             provider.sync_ths_concept_histories()

        # Legacy support for TushareInfo industries
        if source == "tushare_info":
             from vibe_core.data.provider import DataCategory
             import datetime
             if hasattr(provider, "get_industry_list"):
                df = provider.get_industry_list(src="SW2021", level="L1")
                if not df.empty:
                    path = provider.get_save_path(DataCategory.INFO, f"industry_sw2021_{datetime.date.today()}.csv")
                    df.to_csv(path, index=False)
                    print(f"Saved SW2021 industries to {path}")

        print(f"Manual sync for {source} completed.")
    except Exception as e:
        print(f"Manual sync for {source} failed: {e}")
        import traceback
        traceback.print_exc()

@app.post("/api/data/sync")
async def trigger_sync(background_tasks: BackgroundTasks, source: str = "tushare", start_date: str = None, end_date: str = None):
    """Trigger a manual data sync."""
    background_tasks.add_task(_run_manual_sync, source, start_date, end_date)
    return {"status": "started", "message": f"Sync for {source} started in background"}



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle upstream messages
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
