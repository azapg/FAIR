"""Version check endpoint for FAIR platform."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from importlib.metadata import version, PackageNotFoundError

from fastapi import APIRouter
import httpx

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache for PyPI version check (6 hours)
_version_cache: Optional[dict] = None
_cache_timestamp: Optional[datetime] = None
CACHE_DURATION = timedelta(hours=6)


def get_current_version() -> str:
    """Get the current installed version of fair-platform."""
    try:
        return version("fair-platform")
    except PackageNotFoundError:
        # Fallback for development environments
        from pathlib import Path
        import tomllib
        
        path = Path(__file__).resolve()
        for parent in path.parents:
            candidate = parent / "pyproject.toml"
            if candidate.exists():
                try:
                    with candidate.open("rb") as f:
                        data = tomllib.load(f)
                    return data.get("project", {}).get("version", "0.0.0")
                except Exception:
                    break
        return "0.0.0"


async def get_latest_version_from_pypi() -> Optional[str]:
    """Fetch the latest version from PyPI JSON API."""
    global _version_cache, _cache_timestamp
    
    # Check cache
    if _version_cache and _cache_timestamp:
        if datetime.now() - _cache_timestamp < CACHE_DURATION:
            return _version_cache.get("latest")
    
    # Fetch from PyPI
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://pypi.org/pypi/fair-platform/json")
            response.raise_for_status()
            data = response.json()
            latest = data.get("info", {}).get("version")
            
            # Update cache
            _version_cache = {"latest": latest}
            _cache_timestamp = datetime.now()
            
            return latest
    except Exception as e:
        logger.debug(f"Failed to fetch version from PyPI: {e}")
        return None


@router.get("/version")
async def check_version():
    """
    Check current and latest FAIR platform version.
    
    Returns:
        dict: Contains 'current' and 'latest' version strings.
              If unable to fetch latest, 'latest' will match 'current'.
    """
    current = get_current_version()
    latest = await get_latest_version_from_pypi()
    
    # If we couldn't fetch the latest version, return current as latest
    if latest is None:
        latest = current
    
    return {
        "current": current,
        "latest": latest
    }
