"""Version check endpoint for FAIR platform."""
import logging

from fastapi import APIRouter

from fair_platform.utils.version import (
    get_current_version,
    get_latest_version_from_pypi,
    is_version_outdated,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/version")
async def check_version():
    """
    Check current and latest FAIR platform version.
    
    Returns:
        dict: Contains 'current', 'latest', and 'outdated' fields.
              - current: Current installed version
              - latest: Latest available version from PyPI
              - outdated: Boolean indicating if current version is outdated
              If unable to fetch latest, 'latest' will match 'current' and 'outdated' will be False.
    """
    current = get_current_version()
    latest = get_latest_version_from_pypi()
    
    # If we couldn't fetch the latest version, return current as latest
    if latest is None:
        latest = current
    
    outdated = is_version_outdated(current, latest)
    
    return {
        "current": current,
        "latest": latest,
        "outdated": outdated
    }
