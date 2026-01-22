import argparse
import os
import sys
import importlib.util
from typing import Optional

# Ensure current directory is in path
sys.path.append(os.getcwd())

from vibe_core.context import Context
from vibe_core.event import Event
from vibe_core.module import VibeModule
from vibe_core.service import ServiceManager
from vibe_core.backtest.engine import BacktestEngine
from vibe_core.services.scheduler_service import SchedulerService
from vibe_core.services.web_service import WebServerService
from vibe_core.services.module_loader import ModuleLoaderService
from vibe_core.data.hybrid import HybridDataProvider
import time
import threading
import uvicorn
import yaml
from vibe_core.server.server import app

def cmd_new(args):
    """Create a new module"""
    name = args.name
    description = args.description or "No description provided."
    class_name = "".join(x.title() for x in name.split('_'))
    
    # Default to 'beta' folder for new modules
    template_path = os.path.join("templates", "basic_module.py.tpl")
    target_path = os.path.join("modules", "beta", f"{name}.py")
    
    # Ensure beta exists
    if not os.path.exists(os.path.join("modules", "beta")):
        os.makedirs(os.path.join("modules", "beta"))

    if os.path.exists(target_path):
        print(f"Error: Module {name} already exists at {target_path}")
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace("{{ModuleName}}", class_name)
    content = content.replace("{{Description}}", description)
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Success: Created module {class_name} at {target_path}")

def load_module_from_file(path: str) -> Optional[VibeModule]:
    try:
        spec = importlib.util.spec_from_file_location("dynamic_module", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            
            # Find the subclass of VibeModule
            for attribute_name in dir(mod):
                attribute = getattr(mod, attribute_name)
                if isinstance(attribute, type) and issubclass(attribute, VibeModule) and attribute is not VibeModule:
                    return attribute()
    except Exception as e:
        print(f"Failed to load module {path}: {e}")
    return None

def cmd_debug(args):
    """Debug a module"""
    path = args.path
    if not os.path.exists(path):
        print(f"Error: File not found {path}")
        return

    print(f"Debugging module: {path}")
    module = load_module_from_file(path)
    
    if not module:
        print("Error: No VibeModule found in file.")
        return

    # Mock Context
    ctx = Context()
    module.initialize(ctx)
    print(f"Module {module.name} initialized.")

    if args.event:
        # One-off event injection
        import json
        try:
            payload = json.loads(args.event)
            evt = Event(event_type="DEBUG", topic="debug", payload=payload)
            print(f"Injecting event: {evt}")
            module.on_event(evt)
        except json.JSONDecodeError:
            print("Error: Invalid JSON for event")
    else:
        print("Interactive Debug Mode. Type JSON event payload or 'exit'.")
        print("Example: {\"price\": 100}")
        while True:
            try:
                line = input("vibe-debug> ")
                if line.strip() == "exit":
                    break
                if not line.strip():
                    continue
                    
                payload = json.loads(line)
                evt = Event(event_type="DEBUG", topic="debug", payload=payload)
                module.on_event(evt)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

def cmd_list(args):
    """List modules"""
    # Updated to show all folders
    dirs = ["core", "prod", "beta"]
    print(f"{'Module File':<30} | {'Status'}")
    print("-" * 45)
    
    for d in dirs:
        full_d = os.path.join("modules", d)
        if os.path.exists(full_d):
            for f in os.listdir(full_d):
                if f.endswith(".py") and f != "__init__.py":
                    path = os.path.join(d, f)
                    print(f"{path:<30} | Found")

def cmd_backtest(args):
    """Run backtest for a module"""
    path = args.path
    if not os.path.exists(path):
        print(f"Error: File not found {path}")
        return

    module = load_module_from_file(path)
    if not module:
        print("Error: Could not load module")
        return

    engine = BacktestEngine(
        modules=[module],
        start_str=args.start,
        end_str=args.end
    )
    engine.run()

def load_config(path="config/config.yaml"):
    if not os.path.exists(path):
        print(f"Config file not found at {path}, using defaults.")
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def cmd_run(args):
    """Start the VibeStock system in live mode"""
    # Fix for Windows asyncio ProactorEventLoop bug on shutdown
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print("Starting VibeStock System (Hot-Reload Enabled)...")
    
    # 0. Load Config
    config = load_config()
    server_conf = config.get("server", {})
    host = server_conf.get("host", "0.0.0.0")
    port = server_conf.get("port", 8000)
    
    # 1. Initialize Context
    ctx = Context()
    ctx.config = config # Inject config into context

    # 1.1 Initialize Data Provider (Registry)
    # Modules will register themselves into this provider.
    ctx.data = HybridDataProvider()
    print("Data Provider Registry initialized.")
    
    # 2. Create Services
    sched_service = SchedulerService()
    web_service = WebServerService(host=host, port=port)
    loader_service = ModuleLoaderService(ctx) # Automatic module loader
    
    # 3. Inject Dependencies
    ctx._scheduler = sched_service.scheduler
    
    # 4. Register Services
    ServiceManager.register(sched_service)
    ServiceManager.register(web_service)
    ServiceManager.register(loader_service)
    
    # Wire up WebSocket handler to Context routing
    from vibe_core.server.websocket_manager import manager
    manager.set_handler(ctx.handle_client_message)

    # 5. Start All Services
    # The loader_service will immediately scan modules/core, prod, beta and load found modules
    ServiceManager.start_all()
    
    print(f"System started. Web Dashboard: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print("Watching for module changes...")
    
    # 6. Main Loop
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping system...")
        ServiceManager.stop_all()
        print("System stopped.")



def main():
    parser = argparse.ArgumentParser(description="VibeStock CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Command: new
    parser_new = subparsers.add_parser("new", help="Create a new module")
    parser_new.add_argument("name", help="Module name (snake_case), e.g., 'price_monitor'")
    parser_new.add_argument("-d", "--description", help="Module description")

    # Command: debug
    parser_debug = subparsers.add_parser("debug", help="Debug a module")
    parser_debug.add_argument("path", help="Path to module file")
    parser_debug.add_argument("--event", help="JSON string event to inject immediately")

    # Command: list
    parser_list = subparsers.add_parser("list", help="List available modules")

    # Command: backtest
    parser_backtest = subparsers.add_parser("backtest", help="Run backtest")
    parser_backtest.add_argument("path", help="Path to module file")
    parser_backtest.add_argument("--start", required=True, help="Start time (YYYY-MM-DD HH:MM)")
    parser_backtest.add_argument("--end", required=True, help="End time (YYYY-MM-DD HH:MM)")

    # Command: run
    parser_run = subparsers.add_parser("run", help="Start the system in live mode")

    args = parser.parse_args()

    if args.command == "new":
        cmd_new(args)
    elif args.command == "debug":
        cmd_debug(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
