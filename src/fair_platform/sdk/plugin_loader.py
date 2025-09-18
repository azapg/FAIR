from fair_platform.backend import storage

import importlib.util
import os
import sys


def load_plugin_from_module(module_path: str):
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"Module path '{module_path}' does not exist.")

    directory = os.path.dirname(module_path)
    if directory not in sys.path:
        sys.path.append(directory)

    module_name = os.path.splitext(os.path.basename(module_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Error loading module '{module_name}': {e}")


def load_storage_plugins():
    plugins = storage.plugins_dir
    for filename in os.listdir(plugins):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_path = os.path.join(plugins, filename)
            load_plugin_from_module(module_path)


__all__ = [
    "load_storage_plugins",
]
