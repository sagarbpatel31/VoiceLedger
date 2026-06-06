"""Application configuration for VoiceLedger."""

from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "VoiceLedger"
DEFAULT_DATA_DIR = Path("data")
DEFAULT_DATABASE_PATH = DEFAULT_DATA_DIR / "voiceledger.sqlite3"


def get_database_path() -> Path:
    """Return the configured SQLite database path."""
    configured_path = os.getenv("VOICELEDGER_DB_PATH")
    if configured_path:
        return Path(configured_path).expanduser()
    return DEFAULT_DATABASE_PATH
