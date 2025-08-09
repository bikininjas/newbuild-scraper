"""
Database configuration and settings.
"""

import os
from pathlib import Path
from typing import Optional


class DatabaseConfig:
    """Configuration for database operations."""

    def __init__(
        self,
        database_type: str = "sqlite",
        sqlite_path: Optional[str] = None,
        cache_duration_hours: int = 6,
        failed_cache_duration_hours: int = 24,
    ):
        # Force sqlite
        self.database_type = "sqlite"
        self.cache_duration_hours = cache_duration_hours
        self.failed_cache_duration_hours = failed_cache_duration_hours

        # Set default SQLite path if not provided
        if sqlite_path is None:
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            self.sqlite_path = str(data_dir / "scraper.db")
        else:
            self.sqlite_path = sqlite_path

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create config from environment variables."""
        return cls(
            database_type="sqlite",
            sqlite_path=os.getenv("DB_SQLITE_PATH"),
            cache_duration_hours=int(os.getenv("DB_CACHE_HOURS", "6")),
            failed_cache_duration_hours=int(os.getenv("DB_FAILED_CACHE_HOURS", "24")),
        )

    @classmethod
    def from_config_file(cls, config_path: str = "database.conf") -> "DatabaseConfig":
        """Create config from configuration file."""
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip()

        return cls(
            database_type="sqlite",
            sqlite_path=config.get("sqlite_path"),
            cache_duration_hours=int(config.get("cache_duration_hours", "6")),
            failed_cache_duration_hours=int(config.get("failed_cache_duration_hours", "24")),
        )
