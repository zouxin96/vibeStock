import sys
import os
import importlib.util

sys.path.append(os.getcwd())

def test_load(path):
    print(f"Testing load: {path}")
    try:
        spec = importlib.util.spec_from_file_location("test_mod", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print(f"Success: {mod}")
        for attr in dir(mod):
            if attr.endswith("Module"):
                cls = getattr(mod, attr)
                if isinstance(cls, type):
                    print(f"Found Class: {attr}")
                    if hasattr(cls, 'dependencies'):
                        print(f"  Dependencies: {cls.dependencies}")
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

print("--- Checking SinaDataModule ---")
test_load("modules/core/sina_data/__init__.py")

print("\n--- Checking AkShareDataModule ---")
test_load("modules/core/akshare_data/__init__.py")

print("\n--- Checking StockInfoModule ---")
test_load("modules/core/stock_info/__init__.py")
