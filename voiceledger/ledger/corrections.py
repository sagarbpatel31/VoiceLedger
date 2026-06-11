"""Correction log persistence for parsed transaction review edits."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from voiceledger.config import get_database_path


CORRECTION_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS correction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_payload TEXT NOT NULL,
    corrected_payload TEXT NOT NULL,
    changed_fields TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CORRECTION_COLUMNS = ["id", "changed_fields", "original_payload", "corrected_payload", "created_at"]


def initialize_correction_log_table(db_path: str | Path | None = None) -> Path:
    """Create the correction log table if needed."""
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(CORRECTION_SCHEMA_SQL)
        connection.commit()
    return path


def record_correction(
    original_payload: dict[str, Any],
    corrected_payload: dict[str, Any],
    db_path: str | Path | None = None,
) -> int | None:
    """Persist a correction when review edits changed transaction fields."""
    changed_fields = _changed_fields(original_payload, corrected_payload)
    if not changed_fields:
        return None

    path = initialize_correction_log_table(db_path)
    with sqlite3.connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO correction_log (
                original_payload,
                corrected_payload,
                changed_fields,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                json.dumps(original_payload, sort_keys=True),
                json.dumps(corrected_payload, sort_keys=True),
                ", ".join(changed_fields),
                datetime.now().isoformat(sep=" ", timespec="seconds"),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def get_correction_log(db_path: str | Path | None = None) -> pd.DataFrame:
    """Return saved parse correction rows."""
    path = initialize_correction_log_table(db_path)
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT id, changed_fields, original_payload, corrected_payload, created_at
            FROM correction_log
            ORDER BY id DESC
            """
        ).fetchall()
    records = [dict(zip(CORRECTION_COLUMNS, row, strict=True)) for row in rows]
    return pd.DataFrame.from_records(records, columns=CORRECTION_COLUMNS)


def _changed_fields(original_payload: dict[str, Any], corrected_payload: dict[str, Any]) -> list[str]:
    """Return fields whose values changed after review editing."""
    tracked_fields = (
        "transaction_type",
        "item",
        "quantity",
        "unit_price",
        "amount",
        "customer",
        "payment_status",
        "notes",
        "confidence",
    )
    return [field for field in tracked_fields if original_payload.get(field) != corrected_payload.get(field)]


def _resolve_db_path(db_path: str | Path | None) -> Path:
    """Resolve an explicit or configured database path."""
    if db_path is None:
        return get_database_path()
    return Path(db_path).expanduser()
