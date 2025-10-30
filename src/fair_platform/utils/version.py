"""Version checking utilities for CLI."""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx

from fair_platform.backend.data.storage import storage

logger = logging.getLogger(__name__)

# Cache location using storage manager
CACHE_DIR = storage.cache_dir
CACHE_FILE = CACHE_DIR / "last_update_check"
CACHE_DURATION = timedelta(hours=24)


def get_current_version() -> str:
    """Get the current installed version of fair-platform."""
    try:
        # Use the __version__ from the package itself
        from fair_platform import __version__
        return __version__
    except ImportError:
        return "0.0.0"


def should_check_for_updates() -> bool:
    """Check if enough time has passed since the last update check."""
    if not CACHE_FILE.exists():
        return True
    
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            last_check = datetime.fromisoformat(data.get("last_check", ""))
            return datetime.now() - last_check >= CACHE_DURATION
    except Exception:
        return True


def save_check_timestamp(latest_version: str):
    """Save the timestamp and latest version of the last update check."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({
                "last_check": datetime.now().isoformat(),
                "latest_version": latest_version
            }, f)
    except Exception as e:
        logger.debug(f"Failed to save update check timestamp: {e}")


def get_latest_version_from_pypi() -> Optional[str]:
    """Fetch the latest version from PyPI JSON API."""
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get("https://pypi.org/pypi/fair-platform/json")
            response.raise_for_status()
            data = response.json()
            return data.get("info", {}).get("version")
    except Exception as e:
        logger.debug(f"Failed to fetch version from PyPI: {e}")
        return None


def is_version_outdated(current: str, latest: str) -> bool:
    """
    Check if the current version is outdated compared to the latest.
    
    Args:
        current: Current version string
        latest: Latest version string
        
    Returns:
        True if current version is outdated, False otherwise
    """
    if current == latest:
        return False
    
    try:
        from packaging import version as pkg_version
        return pkg_version.parse(latest) > pkg_version.parse(current)
    except Exception:
        # Fail silently if version comparison fails
        return False


def check_for_updates() -> None:
    """
    Check for FAIR platform updates and notify the user if a new version is available.
    
    This function:
    - Respects the FAIR_DISABLE_UPDATE_CHECK environment variable
    - Caches checks for 24 hours
    - Fails silently if offline or if PyPI is unavailable
    - Only prints a message if a newer version is available
    """
    # Check if update checking is disabled
    if os.getenv("FAIR_DISABLE_UPDATE_CHECK"):
        return
    
    # Check if we should perform an update check
    if not should_check_for_updates():
        return
    
    # Get current and latest versions
    current = get_current_version()
    latest = get_latest_version_from_pypi()
    
    # If we couldn't fetch the latest version, don't proceed
    if not latest:
        return
    
    # Compare versions and notify if update available
    if is_version_outdated(current, latest):
        print(f"🔔 New version available: {latest} (current: {current})")
        print("   Run: pip install -U fair-platform")
        # Only save timestamp if we showed a notification
        save_check_timestamp(latest)
