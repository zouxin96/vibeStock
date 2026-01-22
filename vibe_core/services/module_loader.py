from vibe_core.service import IService
from vibe_core.module import VibeModule
from vibe_core.context import Context
import os
import time
import threading
import importlib.util
import sys
import yaml
import logging

class ModuleLoaderService(IService):
    """
    Watches directories (core, prod, beta) and manages module lifecycle.
    Supports:
    - Multi-instance loading via config
    - Dependency management
    - Hot-reloading (for class definitions)
    """
    def __init__(self, context: Context, scan_interval=5):
        self._name = "module_loader"
        self.context = context
        self.scan_interval = scan_interval
        self.running = False
        self._thread = None
        self.logger = logging.getLogger("vibe.loader")
        
        # Structure: path -> timestamp
        self.file_timestamps = {}
        
        # Structure: instance_id -> module_instance
        self.active_instances = {}
        
        # Structure: module_class_name -> class_type
        self.available_classes = {}
        
        # Structure: path -> module_class_name
        self.path_to_class_name = {}
        
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
        self.logger.info(f"Starting module watcher on: {self.watch_dirs}")
        self.running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)

    def _scan_loop(self):
        # Initial scan and load
        self._scan_definitions()
        self._instantiate_modules()
        
        while self.running:
            time.sleep(self.scan_interval)
            if self._scan_definitions():
                # If definitions changed, re-evaluate instances
                self._instantiate_modules()

    def _scan_definitions(self) -> bool:
        """
        Scan directories for VibeModule subclasses. 
        Returns True if any changes were detected.
        """
        changes_detected = False
        current_files = set()
        
        for directory in self.watch_dirs:
            if not os.path.exists(directory): continue
                
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                
                is_package = os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "__init__.py"))
                is_module_file = filename.endswith(".py") and filename != "__init__.py"
                
                if not (is_package or is_module_file): continue
                
                track_path = os.path.join(full_path, "__init__.py") if is_package else full_path
                current_files.add(track_path)
                
                try:
                    mtime = os.path.getmtime(track_path)
                    
                    if track_path not in self.file_timestamps:
                        # New definition
                        self._load_class_definition(track_path)
                        changes_detected = True
                    elif mtime > self.file_timestamps[track_path]:
                        # Modified definition
                        self._load_class_definition(track_path)
                        changes_detected = True
                    
                    self.file_timestamps[track_path] = mtime
                    
                except Exception as e:
                    self.logger.error(f"Error scanning {full_path}: {e}")

        # Check for deleted definitions
        known_files = list(self.file_timestamps.keys())
        for path in known_files:
            if path not in current_files:
                self._unload_class_definition(path)
                changes_detected = True
                del self.file_timestamps[path]
                
        return changes_detected

    def _load_class_definition(self, path: str):
        """Import module file and register VibeModule subclass."""
        self.logger.info(f"Loading definition from: {path}")
        try:
            # Handle package paths
            if path.endswith("__init__.py"):
                module_name = os.path.basename(os.path.dirname(path))
            else:
                module_name = os.path.splitext(os.path.basename(path))[0]
                
            # Use unique spec name to force reload if needed
            spec_name = f"vibe_dyn_{module_name}_{int(time.time())}"
            spec = importlib.util.spec_from_file_location(spec_name, path)
            
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                
                found_class = False
                for attribute_name in dir(mod):
                    attribute = getattr(mod, attribute_name)
                    if isinstance(attribute, type) and issubclass(attribute, VibeModule) and attribute is not VibeModule:
                        # Found a valid module class
                        self.available_classes[attribute.__name__] = attribute
                        self.path_to_class_name[path] = attribute.__name__
                        found_class = True
                        # self.logger.debug(f"Registered class: {attribute.__name__}")
                
                if not found_class:
                    self.logger.warning(f"No VibeModule subclass found in {path}")
                    
        except Exception as e:
            self.logger.error(f"Failed to import {path}: {e}")
            import traceback
            traceback.print_exc()

    def _unload_class_definition(self, path: str):
        if path in self.path_to_class_name:
            class_name = self.path_to_class_name[path]
            if class_name in self.available_classes:
                del self.available_classes[class_name]
            del self.path_to_class_name[path]
            
            # Stop all instances of this class
            to_remove = [iid for iid, inst in self.active_instances.items() if inst.__class__.__name__ == class_name]
            for iid in to_remove:
                self._stop_instance(iid)

    def _instantiate_modules(self):
        """
        Reconcile desired instances with active instances.
        Reads config/instances.yaml or uses defaults.
        """
        # 1. Determine Desired State
        desired_instances = [] # List of dicts: {id, class_name, config}
        
        config_path = os.path.join("config", "instances.yaml")
        
        # Load explicit config if exists
        explicit_config = False
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and "instances" in data:
                        explicit_config = True
                        for item in data["instances"]:
                            desired_instances.append(item)
            except Exception as e:
                self.logger.error(f"Error loading instances.yaml: {e}")

        # If no explicit config for a class, add a default instance
        # This ensures backward compatibility and "plug-and-play"
        existing_configured_classes = set(item['module'] for item in desired_instances)
        
        for class_name in self.available_classes:
            # If we haven't explicitly configured instances for this class, create a default one
            # OR if we want to allow default instances ALONGSIDE explicit ones? 
            # Usually if explicit config exists, we probably want full control.
            # But here, let's say: if class is NOT in instances.yaml, load default.
            if class_name not in existing_configured_classes:
                # Default ID is the snake_case version of class name usually, or just class name
                desired_instances.append({
                    "id": class_name,
                    "module": class_name,
                    "config": {} # Will verify if individual module config yaml exists later
                })

        # 2. Dependency Ordering (Simple topological sort or multi-pass)
        # We need to know dependencies of classes.
        # Ideally, we instantiate, check deps, if missing, wait.
        # But VibeModule dependencies are instance attributes? No, usually class attributes or known.
        # Let's assume we can just try to load, and if deps missing, retry next pass?
        # Actually, let's implement a multi-pass loader.
        
        pending_instances = desired_instances[:]
        loaded_in_this_pass = True
        
        while pending_instances and loaded_in_this_pass:
            loaded_in_this_pass = False
            retry_list = []
            
            for item in pending_instances:
                iid = item['id']
                class_name = item['module']
                
                # Check if class is available
                if class_name not in self.available_classes:
                    self.logger.warning(f"Class {class_name} not found for instance {iid}")
                    continue
                
                # Check if already running
                if iid in self.active_instances:
                    # TODO: Check if config changed and reload? For now, skip.
                    continue
                
                # Check Dependencies
                # We need to instantiate temporarily or check class attribute to know dependencies?
                # Let's inspect the class attribute 'dependencies' if it exists.
                cls = self.available_classes[class_name]
                # Default to empty list if not defined on class
                deps = getattr(cls, 'dependencies', []) 
                # Note: 'dependencies' on VibeModule instance is what we used before.
                # If it's defined in __init__, we can't see it without instantiating.
                # We encourage defining it as class attribute or we optimistically load.
                
                missing_deps = [d for d in deps if not self._is_module_active(d)]
                
                if missing_deps:
                    # Dependencies not ready yet
                    # Check if these deps are even in our desired list? 
                    # If not, this module will never load.
                    # For now, put in retry list.
                    self.logger.debug(f"Instance {iid} ({class_name}) missing deps: {missing_deps}")
                    retry_list.append(item)
                else:
                    # Ready to load
                    self._start_instance(iid, class_name, item.get('config', {}))
                    loaded_in_this_pass = True
            
            pending_instances = retry_list

        if pending_instances:
            self.logger.warning(f"Some modules could not be loaded due to missing dependencies or errors: {[i['id'] for i in pending_instances]}")
            for i in pending_instances:
                cls_name = i['module']
                if cls_name in self.available_classes:
                    deps = getattr(self.available_classes[cls_name], 'dependencies', [])
                    missing = [d for d in deps if not self._is_module_active(d)]
                    self.logger.warning(f"  - {i['id']}: Missing {missing}")

        # 3. Cleanup: Stop instances that are no longer in desired list
        desired_ids = set(item['id'] for item in desired_instances)
        active_ids = list(self.active_instances.keys())
        for iid in active_ids:
            if iid not in desired_ids:
                self._stop_instance(iid)

    def _is_module_active(self, module_name_or_id: str) -> bool:
        """Check if a module is active by ID or Class Name."""
        # Check IDs
        if module_name_or_id in self.active_instances:
            return True
        # Check Class Names
        for inst in self.active_instances.values():
            if inst.__class__.__name__ == module_name_or_id:
                return True
        return False

    def _start_instance(self, instance_id: str, class_name: str, config: dict):
        self.logger.info(f"Starting instance: {instance_id} ({class_name})")
        try:
            cls = self.available_classes[class_name]
            instance = cls()
            
            # Override attributes
            instance.name = instance_id # Set the instance name to the ID
            
            # Load specific config file if exists (modules/instance_id.yaml)
            # OR modules/class_name.yaml
            # Precedence: Explicit Config arg > Instance YAML > Class YAML
            
            # 1. Class YAML
            class_conf_path = os.path.join("config", "modules", f"{class_name}.yaml")
            if os.path.exists(class_conf_path):
                with open(class_conf_path, 'r', encoding='utf-8') as f:
                    instance.config.update(yaml.safe_load(f) or {})
            
            # 2. Instance YAML (if ID differs from class name)
            if instance_id != class_name:
                inst_conf_path = os.path.join("config", "modules", f"{instance_id}.yaml")
                if os.path.exists(inst_conf_path):
                    with open(inst_conf_path, 'r', encoding='utf-8') as f:
                        instance.config.update(yaml.safe_load(f) or {})
            
            # 3. Explicit Config
            instance.config.update(config)

            # Register UI Routes
            ui_configs = instance.get_ui_config()
            if ui_configs:
                if not isinstance(ui_configs, list): ui_configs = [ui_configs]
                for cfg in ui_configs:
                    if "id" in cfg:
                        # Allow instance config to override UI widget ID to avoid conflicts?
                        # If multiple instances of same class, they'd conflict on default Widget ID.
                        # We should suffix the widget ID with instance ID if it's not the default one?
                        
                        # LOGIC: If we have multiple instances, we MUST have unique widget IDs.
                        # The module should probably handle this by using self.name in get_ui_config,
                        # OR we dynamically patch it here.
                        
                        # Let's patch it if the instance.name != default class name
                        if instance.name != class_name and cfg['id'] == getattr(cls(), 'get_ui_config', lambda: {'id':''})().get('id'):
                             # If the ID is just the default one, we append instance name
                             cfg['id'] = f"{cfg['id']}_{instance.name}"
                             cfg['title'] = f"{cfg.get('title', '')} ({instance.name})"
                        
                        self.context.register_module_instance(cfg["id"], instance)

            instance.initialize(self.context)
            self.active_instances[instance_id] = instance
            
        except Exception as e:
            self.logger.error(f"Failed to start instance {instance_id}: {e}")
            import traceback
            traceback.print_exc()

    def _stop_instance(self, instance_id: str):
        self.logger.info(f"Stopping instance: {instance_id}")
        if instance_id in self.active_instances:
            instance = self.active_instances[instance_id]
            try:
                instance.on_stop()
            except Exception as e:
                self.logger.error(f"Error stopping {instance_id}: {e}")
            
            self.context.deregister_module(instance_id)
            del self.active_instances[instance_id]
