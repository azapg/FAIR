from pathlib import Path

from fair_platform.backend.data.storage import PlatformStorage


def test_fair_data_dir_overrides_platform_data_directory(
    monkeypatch,
    tmp_path: Path,
):
    persistent_dir = tmp_path / "persistent-data"
    monkeypatch.setenv("FAIR_DATA_DIR", str(persistent_dir))

    configured_storage = PlatformStorage()

    assert configured_storage.data_dir == persistent_dir
    assert configured_storage.local_db_path == persistent_dir / "fair.db"
    assert configured_storage.uploads_dir == persistent_dir / "uploads"
    assert configured_storage.plugins_dir == persistent_dir / "plugins"
