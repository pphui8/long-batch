from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    user_agent: str
    request_timeout_seconds: float
    request_delay_seconds: float
    index_urls: tuple[str, ...]

    @property
    def laws_dir(self) -> Path:
        return self.data_dir / "laws"

    @property
    def state_dir(self) -> Path:
        return self.data_dir / "state"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"


def load_settings() -> Settings:
    index_urls = tuple(
        url.strip()
        for url in os.getenv("NATIONAL_LAW_DB_INDEX_URLS", "").split(",")
        if url.strip()
    )
    return Settings(
        data_dir=Path(os.getenv("LAW_DATA_DIR", "/app/legislation")).resolve(),
        user_agent=os.getenv(
            "LAW_SYNC_USER_AGENT",
            "long-batch/0.1 legislation-sync contact=local",
        ),
        request_timeout_seconds=float(os.getenv("LAW_SYNC_REQUEST_TIMEOUT_SECONDS", "30")),
        request_delay_seconds=float(os.getenv("LAW_SYNC_REQUEST_DELAY_SECONDS", "0.5")),
        index_urls=index_urls,
    )
