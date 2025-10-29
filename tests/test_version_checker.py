"""Tests for version checking functionality."""
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
import httpx

from fair_platform.backend.api.routers.version import (
    get_current_version,
    get_latest_version_from_pypi,
    check_version,
)
from fair_platform.utils.version import (
    should_check_for_updates,
    save_check_timestamp,
    check_for_updates,
)


class TestBackendVersionEndpoint:
    """Test the backend /api/version endpoint."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear the cache before each test."""
        from fair_platform.backend.api.routers import version as version_module
        version_module._version_cache = None
        version_module._cache_timestamp = None
        yield

    def test_get_current_version(self):
        """Test getting the current version."""
        version = get_current_version()
        assert version is not None
        assert isinstance(version, str)
        # Should be a valid version string
        assert len(version) > 0

    @pytest.mark.asyncio
    async def test_get_latest_version_from_pypi_success(self):
        """Test successful PyPI version fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "info": {"version": "1.0.0"}
        }
        mock_response.raise_for_status = Mock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            latest = await get_latest_version_from_pypi()
            assert latest == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_latest_version_from_pypi_failure(self):
        """Test PyPI fetch failure handling."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.TimeoutException("Timeout")
            
            latest = await get_latest_version_from_pypi()
            assert latest is None

    @pytest.mark.asyncio
    async def test_check_version_endpoint(self):
        """Test the version check endpoint."""
        result = await check_version()
        
        assert "current" in result
        assert "latest" in result
        assert isinstance(result["current"], str)
        assert isinstance(result["latest"], str)

    @pytest.mark.asyncio
    async def test_check_version_offline_fallback(self):
        """Test that offline returns current version as latest."""
        with patch(
            "fair_platform.backend.api.routers.version.get_latest_version_from_pypi",
            return_value=None
        ):
            result = await check_version()
            
            # When offline, latest should equal current
            assert result["current"] == result["latest"]

    @pytest.mark.asyncio
    async def test_version_caching(self):
        """Test that version results are cached."""
        # First call should hit PyPI
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"info": {"version": "1.5.0"}}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            latest1 = await get_latest_version_from_pypi()
            assert latest1 == "1.5.0"
            
            # Reset cache timestamp to make it valid
            from fair_platform.backend.api.routers import version as version_module
            version_module._cache_timestamp = datetime.now()
            
            # Second call should use cache (no PyPI hit)
            latest2 = await get_latest_version_from_pypi()
            assert latest2 == "1.5.0"
            
            # Verify PyPI was only called once
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 1


class TestCLIVersionChecker:
    """Test CLI version checking utilities."""

    @pytest.fixture(autouse=True)
    def setup_cache_dir(self, tmp_path, monkeypatch):
        """Setup temporary cache directory for tests."""
        test_cache = tmp_path / ".cache" / "fair"
        test_cache.mkdir(parents=True, exist_ok=True)
        test_cache_file = test_cache / "last_update_check"
        
        monkeypatch.setattr("fair_platform.utils.version.CACHE_DIR", test_cache)
        monkeypatch.setattr("fair_platform.utils.version.CACHE_FILE", test_cache_file)
        
        yield test_cache_file

    def test_should_check_for_updates_no_cache(self, setup_cache_dir):
        """Test that update check is needed when cache doesn't exist."""
        assert should_check_for_updates() is True

    def test_should_check_for_updates_cache_expired(self, setup_cache_dir):
        """Test that update check is needed when cache is expired."""
        # Create old cache entry
        old_time = datetime.now() - timedelta(hours=25)
        with open(setup_cache_dir, "w") as f:
            json.dump({
                "last_check": old_time.isoformat(),
                "latest_version": "1.0.0"
            }, f)
        
        assert should_check_for_updates() is True

    def test_should_check_for_updates_cache_valid(self, setup_cache_dir):
        """Test that update check is skipped when cache is valid."""
        # Create recent cache entry
        recent_time = datetime.now() - timedelta(hours=1)
        with open(setup_cache_dir, "w") as f:
            json.dump({
                "last_check": recent_time.isoformat(),
                "latest_version": "1.0.0"
            }, f)
        
        assert should_check_for_updates() is False

    def test_save_check_timestamp(self, setup_cache_dir):
        """Test saving the check timestamp."""
        save_check_timestamp("1.2.3")
        
        assert setup_cache_dir.exists()
        with open(setup_cache_dir, "r") as f:
            data = json.load(f)
            assert "last_check" in data
            assert data["latest_version"] == "1.2.3"

    def test_check_for_updates_disabled_by_env(self, monkeypatch, capsys):
        """Test that FAIR_DISABLE_UPDATE_CHECK prevents checking."""
        monkeypatch.setenv("FAIR_DISABLE_UPDATE_CHECK", "1")
        
        check_for_updates()
        
        captured = capsys.readouterr()
        assert "New version available" not in captured.out

    def test_check_for_updates_no_new_version(self, monkeypatch, capsys):
        """Test that no message is printed when versions match."""
        monkeypatch.setattr(
            "fair_platform.utils.version.get_current_version",
            lambda: "1.0.0"
        )
        monkeypatch.setattr(
            "fair_platform.utils.version.get_latest_version_from_pypi",
            lambda: "1.0.0"
        )
        monkeypatch.setattr(
            "fair_platform.utils.version.should_check_for_updates",
            lambda: True
        )
        
        check_for_updates()
        
        captured = capsys.readouterr()
        assert "New version available" not in captured.out

    def test_check_for_updates_new_version_available(self, monkeypatch, capsys):
        """Test that message is printed when new version is available."""
        monkeypatch.setattr(
            "fair_platform.utils.version.get_current_version",
            lambda: "1.0.0"
        )
        monkeypatch.setattr(
            "fair_platform.utils.version.get_latest_version_from_pypi",
            lambda: "2.0.0"
        )
        monkeypatch.setattr(
            "fair_platform.utils.version.should_check_for_updates",
            lambda: True
        )
        
        check_for_updates()
        
        captured = capsys.readouterr()
        assert "New version available: 2.0.0" in captured.out
        assert "current: 1.0.0" in captured.out
        assert "pip install -U fair-platform" in captured.out

    def test_check_for_updates_offline(self, monkeypatch, capsys):
        """Test that offline scenario doesn't crash."""
        monkeypatch.setattr(
            "fair_platform.utils.version.should_check_for_updates",
            lambda: True
        )
        monkeypatch.setattr(
            "fair_platform.utils.version.get_latest_version_from_pypi",
            lambda: None
        )
        
        # Should not raise any exception
        check_for_updates()
        
        captured = capsys.readouterr()
        # No error message should be printed
        assert "New version available" not in captured.out

    def test_check_for_updates_respects_cache(self, monkeypatch, capsys):
        """Test that version check respects the cache."""
        monkeypatch.setattr(
            "fair_platform.utils.version.should_check_for_updates",
            lambda: False
        )
        
        # Mock these to verify they're not called
        mock_get_current = Mock(return_value="1.0.0")
        mock_get_latest = Mock(return_value="2.0.0")
        
        monkeypatch.setattr(
            "fair_platform.utils.version.get_current_version",
            mock_get_current
        )
        monkeypatch.setattr(
            "fair_platform.utils.version.get_latest_version_from_pypi",
            mock_get_latest
        )
        
        check_for_updates()
        
        # Should not have called version fetching functions
        mock_get_current.assert_not_called()
        mock_get_latest.assert_not_called()
        
        captured = capsys.readouterr()
        assert "New version available" not in captured.out
