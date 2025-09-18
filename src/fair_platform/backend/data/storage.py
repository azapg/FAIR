from pathlib import Path
import appdirs


class PlatformStorage:
    def __init__(self):
        self.app_name = "fair-platform"
        self.app_author = "fair-group"

        self.data_dir = Path(appdirs.user_data_dir(self.app_name, self.app_author))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.config_dir = Path(appdirs.user_config_dir(self.app_name, self.app_author))
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.cache_dir = Path(appdirs.user_cache_dir(self.app_name, self.app_author))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def local_db_path(self):
        return self.data_dir / "fair.db"

    @property
    def plugins_dir(self):
        plugins_dir = self.data_dir / "plugins"
        plugins_dir.mkdir(exist_ok=True)
        return plugins_dir

    @property
    def uploads_dir(self):
        upload_dir = self.data_dir / "uploads"
        upload_dir.mkdir(exist_ok=True)
        return upload_dir

    def get_config_path(self, filename):
        return self.config_dir / filename


storage = PlatformStorage()
