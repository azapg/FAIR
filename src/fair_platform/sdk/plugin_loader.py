from fair_platform.backend import storage

import importlib.util
import os
import sys
from typing import Optional


def load_plugin_from_module(module_path: str) -> Optional[object]:
    """
    Load a plugin module from a file path. Registers the module under a unique name
    based on the plugin directory to avoid name collisions (e.g. plugin_<dirname>).
    Returns the loaded module or None on failure.
    """
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"Module path '{module_path}' does not exist.")

    directory = os.path.dirname(module_path)
    plugin_name = os.path.basename(directory)
    module_name = f"plugin_{plugin_name}"

    if directory not in sys.path:
        sys.path.append(directory)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load specification for module '{module_name}' from '{module_path}'.")

    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"Error loading module '{module_name}' from '{module_path}': {e}")
        return None


def load_storage_plugins():
    """
    Load plugins from storage.plugins_dir. Each plugin is expected to be a directory
    that does NOT start with '__' or '.' and must contain a 'main.py' file which will be loaded.
    """
    plugins_root = storage.plugins_dir
    if not plugins_root:
        return

    if not os.path.exists(plugins_root):
        return

    for entry in os.listdir(plugins_root):
        if entry.startswith("__") or entry.startswith("."):
            continue

        full_path = os.path.join(plugins_root, entry)
        if not os.path.isdir(full_path):
            continue

        main_py = os.path.join(full_path, "main.py")
        if os.path.exists(main_py) and os.path.isfile(main_py):
            load_plugin_from_module(main_py)


__all__ = [
    "load_storage_plugins",
]
