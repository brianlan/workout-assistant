"""Application configuration."""

import os
from pathlib import Path


class Settings:
    """Application settings loaded from environment variables with defaults."""

    def __init__(self) -> None:
        self.data_dir: Path = Path(os.getenv("DATA_DIR", "./data")).resolve()
        self.port: int = int(os.getenv("PORT", "8000"))
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.db_url: str = f"sqlite:///{self.data_dir / 'workout.db'}"
        self.videos_dir: Path = self.data_dir / "videos"
        self.thumbnails_dir: Path = self.data_dir / "thumbnails"
        self.config_path: Path = self.data_dir / "config.json"


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
