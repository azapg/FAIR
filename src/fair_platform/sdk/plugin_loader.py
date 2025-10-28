import contextlib
import hashlib
import threading
from pathlib import Path
from types import ModuleType

from fair_platform.backend import storage

import importlib.util
import os
import sys
from typing import Optional

from fair_platform.sdk.loader_utils import venv_exists, create_venv, simple_check_requirements, load_requirements, \
    install_requirements, get_site_packages_path

sys_path_lock = threading.Lock()

excluded = {".DS_Store", "__pycache__"}

def add_plugin_site_packages(venv_dir: str) -> None:
    venv_site_packages = get_site_packages_path(venv_dir)

    if venv_site_packages and Path(venv_site_packages).is_dir():
        if venv_site_packages not in sys.path:
            sys.path.insert(0, venv_site_packages)
    else:
        print(f"Warning: Could not find site-packages directory for venv at {venv_dir}")

def hash_extension_folder(folder: Path):
    hash_builder = hashlib.sha256()
    files = sorted(
        file
        for file in folder.rglob("*")
        if file.is_file() and file.name not in excluded
    )
    for file in files:
        with open(file, "rb") as f:
            while chunk := f.read(8192):
                hash_builder.update(chunk)
    return hash_builder.hexdigest()


def get_folder_modules(folder: Path):
    return [
        file
        for file in folder.rglob("*.py")
        if file.is_file() and file.name not in excluded
    ]


def load_plugin_from_module(module_path: str, venv_path: Optional[str] = None) -> Optional[ModuleType]:
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
        raise ImportError(
            f"Could not load specification for module '{module_name}' from '{module_path}'."
        )

    module = importlib.util.module_from_spec(spec)

    directory_path = Path(directory)
    extension_hash = hash_extension_folder(directory_path)

    setattr(module, "__extension_hash__", extension_hash)
    setattr(module, "__extension_dir__", plugin_name)
    sys.modules[module_name] = module

    try:
        if venv_path and venv_exists(venv_path):
            add_plugin_site_packages(venv_path)
            spec.loader.exec_module(module)
            return module
        else:
            spec.loader.exec_module(module)
            return module
    except Exception as e:
        print(f"Error loading module '{module_name}' from '{module_path}': {e}")
        del sys.modules[module_name]
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

        print(f"Processing extension '{entry}'...")

        venv_path = os.path.join(full_path, ".venv")
        if venv_exists(venv_path):
            print(f"Found extension '{entry}' virtual environment")
        else:
            print(f"Creating extension '{entry}' virtual environment...'")
            create_venv(venv_path)
            print(f"Created extension '{entry}' virtual environment")

        extension_requirements = load_requirements(os.path.join(full_path, "requirements.txt"))
        if not simple_check_requirements(venv_path, extension_requirements):
            print(f"Installing extension '{entry}' requirements...'")
            install_requirements(venv_path, extension_requirements)
            print(f"Installed extension '{entry}' requirements")

        main_py = os.path.join(full_path, "main.py")
        if os.path.exists(main_py) and os.path.isfile(main_py):
            # TODO: Maybe do a "load_plugin_from_folder", that loads all modules and injects hash metadata into them.
            module = load_plugin_from_module(main_py, venv_path=venv_path)
            if module:
                print(f"Loaded extension '{entry}'")
            else:
                print(f"Failed to load extension '{entry}'")


__all__ = [
    "load_storage_plugins",
]
