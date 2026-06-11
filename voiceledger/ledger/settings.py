"""Business settings persistence for VoiceLedger."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from voiceledger.config import get_database_path


SETTINGS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS business_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_BUSINESS_SETTINGS = {
    "business_name": "VoiceLedger Seller",
    "currency_symbol": "₹",
    "low_stock_threshold": "5",
    "language_style": "English + Hinglish",
    "field_test_who": "A local informal seller who tracks sales, stock, customer dues, and profit from short notes.",
    "field_test_tried": "Voice notes, typed notes, customer credit, inventory updates, dashboard review, and exports.",
    "field_test_changed": "Added review warnings, save receipts, edit/delete, CSV export, and clearer demo health.",
    "field_test_checklist": "Record sale,Record expense,Customer owes,Customer paid,Bought stock,Review dashboard,Export report",
}


def initialize_business_settings_table(db_path: str | Path | None = None) -> Path:
    """Create the business settings table and seed default values."""
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(SETTINGS_SCHEMA_SQL)
        connection.executemany(
            """
            INSERT OR IGNORE INTO business_settings (key, value)
            VALUES (?, ?)
            """,
            DEFAULT_BUSINESS_SETTINGS.items(),
        )
        connection.commit()

    return path


def get_business_settings(db_path: str | Path | None = None) -> dict[str, str]:
    """Return business settings merged with defaults."""
    path = initialize_business_settings_table(db_path)
    with sqlite3.connect(path) as connection:
        rows = connection.execute("SELECT key, value FROM business_settings").fetchall()

    settings = dict(DEFAULT_BUSINESS_SETTINGS)
    settings.update({str(key): str(value) for key, value in rows})
    return settings


def update_business_settings(
    business_name: str | None = None,
    currency_symbol: str | None = None,
    low_stock_threshold: float | int | str | None = None,
    language_style: str | None = None,
    db_path: str | Path | None = None,
    **extra_settings: str | None,
) -> dict[str, str]:
    """Update business settings and return the merged settings."""
    path = initialize_business_settings_table(db_path)
    updates: dict[str, str] = {}
    if business_name is not None:
        updates["business_name"] = _clean_text(business_name, DEFAULT_BUSINESS_SETTINGS["business_name"])
    if currency_symbol is not None:
        updates["currency_symbol"] = _clean_text(currency_symbol, DEFAULT_BUSINESS_SETTINGS["currency_symbol"])
    if low_stock_threshold is not None:
        updates["low_stock_threshold"] = str(_coerce_threshold(low_stock_threshold))
    if language_style is not None:
        updates["language_style"] = _clean_text(language_style, DEFAULT_BUSINESS_SETTINGS["language_style"])

    for key, value in extra_settings.items():
        if key in DEFAULT_BUSINESS_SETTINGS and value is not None:
            updates[key] = _clean_text(value, DEFAULT_BUSINESS_SETTINGS[key])

    if updates:
        with sqlite3.connect(path) as connection:
            connection.executemany(
                """
                INSERT INTO business_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                updates.items(),
            )
            connection.commit()

    return get_business_settings(path)


def get_low_stock_threshold(db_path: str | Path | None = None) -> float:
    """Return the configured low-stock threshold as a float."""
    settings = get_business_settings(db_path)
    return _coerce_threshold(settings.get("low_stock_threshold", DEFAULT_BUSINESS_SETTINGS["low_stock_threshold"]))


def _coerce_threshold(value: float | int | str) -> float:
    """Return a non-negative low-stock threshold."""
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        threshold = float(DEFAULT_BUSINESS_SETTINGS["low_stock_threshold"])
    return max(threshold, 0.0)


def _clean_text(value: str, default: str) -> str:
    """Normalize a setting string."""
    cleaned = " ".join(str(value or "").split()).strip()
    return cleaned or default


def _resolve_db_path(db_path: str | Path | None) -> Path:
    """Resolve an explicit or configured database path."""
    if db_path is None:
        return get_database_path()
    return Path(db_path).expanduser()
