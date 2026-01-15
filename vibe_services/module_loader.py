from vibe_core.service import IService
from vibe_core.module import VibeModule
from vibe_core.context import Context
import os
import time
import threading
import importlib.util
import sys

import yaml

class ModuleLoaderService(IService):
    """
    Watches directories (core, prod, beta) and automatically loads/reloads modules.
    """
    def __init__(self, context: Context, scan_interval=5):
        self._name = "module_loader"
        self.context = context
        self.scan_interval = scan_interval
        self.running = False
        self._thread = None
        
        # Structure: path -> timestamp
        self.file_timestamps = {}
        # Structure: path -> module_name
        self.loaded_modules = {} 
        
        self.watch_dirs = [
            os.path.join("modules", "core"),
            os.path.join("modules", "prod"),
            os.path.join("modules", "beta")
        ]
        
        # Ensure dirs exist
        for d in self.watch_dirs:
            if not os.path.exists(d):
                os.makedirs(d)

    @property
    def name(self) -> str:
        return self._name

    def start(self):
        print(f"[{self.name}] Starting watcher on: {self.watch_dirs}")
        self.running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)

    def _scan_loop(self):
        # Initial scan
        self._scan()
        
        while self.running:
            time.sleep(self.scan_interval)
            self._scan()

    def _scan(self):
        """
        Check all directories for changes.
        """
        current_files = set()
        
        for directory in self.watch_dirs:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                
                is_package = os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "__init__.py"))
                is_module_file = filename.endswith(".py") and filename != "__init__.py"
                
                if not (is_package or is_module_file):
                    continue
                
                # For packages, we track the timestamp of __init__.py or the dir itself?
                # Changing files inside package should trigger reload.
                # Simplest: Track __init__.py for packages.
                
                track_path = os.path.join(full_path, "__init__.py") if is_package else full_path
                
                current_files.add(track_path)
                
                try:
                    mtime = os.path.getmtime(track_path)
                    
                    if track_path not in self.file_timestamps:
                        # NEW FILE
                        self._load_module(track_path)
                    elif mtime > self.file_timestamps[track_path]:
                        # MODIFIED FILE
                        self._reload_module(track_path)
                    
                    self.file_timestamps[track_path] = mtime
                    
                except Exception as e:
                    print(f"[{self.name}] Error scanning {full_path}: {e}")

        # Check for DELETED files
        known_files = list(self.file_timestamps.keys())
        for path in known_files:
            if path not in current_files:
                self._unload_module(path)
                del self.file_timestamps[path]

    def _load_module(self, path: str):
        print(f"[{self.name}] Detected new module: {path}")
        mod_instance = self._import_module(path)
        if mod_instance:
            # Load Config if exists
            config_path = os.path.join("config", "modules", f"{mod_instance.name}.yaml")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        mod_config = yaml.safe_load(f)
                        if mod_config:
                            mod_instance.config.update(mod_config)
                            print(f"[{self.name}] Loaded config for {mod_instance.name}")
                except Exception as e:
                     print(f"[{self.name}] Failed to load config for {mod_instance.name}: {e}")

            # Register with Context for Message Routing (New)
            if hasattr(self.context, 'register_module_instance'):
                 # Use module.get_ui_config() to find the ID(s) it handles?
                 # Or just use module class name?
                 # The UI sends "moduleId" which corresponds to the "id" in get_ui_config().
                 # A module might return a LIST of configs with different IDs.
                 ui_configs = mod_instance.get_ui_config()
                 if ui_configs:
                     if not isinstance(ui_configs, list): ui_configs = [ui_configs]
                     for cfg in ui_configs:
                         if "id" in cfg:
                             self.context.register_module_instance(cfg["id"], mod_instance)

            mod_instance.initialize(self.context)
            self.loaded_modules[path] = mod_instance.name
            print(f"[{self.name}] Successfully loaded {mod_instance.name}")

    def _reload_module(self, path: str):
        print(f"[{self.name}] Detected change in module: {path}")
        self._unload_module(path)
        self._load_module(path)

    def _unload_module(self, path: str):
        if path in self.loaded_modules:
            mod_name = self.loaded_modules[path]
            print(f"[{self.name}] Unloading module: {mod_name}")
            
            # Clean up resources via Context
            self.context.deregister_module(mod_name)
            
            del self.loaded_modules[path]

    def _import_module(self, path: str):
        """
        Dynamically imports a module from file path.
        """
        try:
            # We use a unique name for the spec to avoid sys.modules collision if needed,
            # but usually just file path base is fine.
            module_name = os.path.splitext(os.path.basename(path))[0]
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                
                # Find VibeModule subclass
                for attribute_name in dir(mod):
                    attribute = getattr(mod, attribute_name)
                    if isinstance(attribute, type) and issubclass(attribute, VibeModule) and attribute is not VibeModule:
                        return attribute()
        except Exception as e:
            print(f"[{self.name}] Failed to import {path}: {e}")
            import traceback
            traceback.print_exc()
        return None
