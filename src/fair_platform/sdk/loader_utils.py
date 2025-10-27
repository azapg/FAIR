import os
import subprocess
import json
import venv

__all__ = [
    "get_venv_python",
    "get_venv_pip",
    "venv_exists",
    "create_venv",
    "load_requirements",
    "install_requirements",
    "list_outdated_packages",
    "list_installed_packages",
    "simple_check_requirements",
    "get_site_packages_path"
]

def get_venv_python(venv_path: str) -> str:
    if os.name == "nt":
        return os.path.join(venv_path, "Scripts", "python.exe")
    else:
        return os.path.join(venv_path, "bin", "python")

def get_venv_pip(venv_path: str) -> str:
    if os.name == "nt":
        return os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        return os.path.join(venv_path, "bin", "pip")

def venv_exists(venv_path: str) -> bool:
    return os.path.isdir(venv_path) and os.path.isfile(get_venv_python(venv_path))

def create_venv(venv_path: str):
    if not os.path.exists(venv_path):
        venv.create(venv_path, with_pip=True)

def load_requirements(requirements_path: str) -> list[str]:
    requirements = []
    if os.path.isfile(requirements_path):
        with open(requirements_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    requirements.append(line)
    return requirements

def install_requirements(venv_path: str, requirements: list[str]):
    pip_path = get_venv_pip(venv_path)
    if requirements:
        # TODO: Add a env variable to make stricter requirements checking
        subprocess.run([pip_path, "install"] + requirements, check=True)

def list_outdated_packages(venv_path: str) -> list[dict]:
    pip_path = get_venv_pip(venv_path)
    result = subprocess.run([pip_path, "list", "--outdated", "--format=json"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to list outdated packages: {result.stderr}")
    return json.loads(result.stdout) if result.stdout else []

def list_installed_packages(venv_path: str) -> dict[str, str]:
    pip_path = get_venv_pip(venv_path)
    result = subprocess.run([pip_path, "list", "--format=json"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to list installed packages: {result.stderr}")
    packages = json.loads(result.stdout) if result.stdout else []
    return {pkg["name"].lower(): pkg["version"] for pkg in packages}

def simple_check_requirements(venv_path: str, requirements: list[str]) -> bool:
    installed = list_installed_packages(venv_path)
    for req in requirements:
        pkg_name = req.split("==")[0].split(">=")[0].split("<=")[0].lower()
        if pkg_name not in installed:
            return False
    return True

def get_site_packages_path(venv_path: str) -> str:
    if os.name == "nt":
        return os.path.join(venv_path, "Lib", "site-packages")
    else:
        py_version = f"python{os.sys.version_info.major}.{os.sys.version_info.minor}"
        return os.path.join(venv_path, "lib", py_version, "site-packages")