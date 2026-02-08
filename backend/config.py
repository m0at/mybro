"""mybro configuration. All tunables in one place."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DBConfig:
    postgres_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL", "postgresql://andy@localhost:5432/mybro"
        )
    )
    redis_url: str = field(
        default_factory=lambda: os.environ.get("REDIS_URL", "redis://localhost:6379")
    )
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("MYBRO_DATA_DIR", str(Path.home() / ".mybro")))
    )

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "tracking.db"

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "screenshots").mkdir(exist_ok=True)


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 9000
    frontend_origins: list = field(
        default_factory=lambda: [
            "http://localhost:9001",
            "http://127.0.0.1:9001",
        ]
    )


@dataclass
class TrackerConfig:
    screenshot_interval_s: int = 20
    screenshot_region_px: int = 400
    screenshot_quality: int = 60
    afk_threshold_s: int = 180
    input_aggregate_interval_s: int = 60
    classifier_model: str = "claude-haiku-4-5-20251001"


@dataclass
class TPMConfig:
    model: str = "claude-sonnet-4-5-20250929"
    claude_cli_path: str = "claude"
    max_fix_timeout_s: int = 120


@dataclass
class Config:
    db: DBConfig = field(default_factory=DBConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    tpm: TPMConfig = field(default_factory=TPMConfig)
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    digitalocean_token: str = field(
        default_factory=lambda: os.environ.get("DIGITALOCEAN_TOKEN", "")
    )


config = Config()
