"""Inventory stock persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from voiceledger.config import get_database_path


INVENTORY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS inventory (
    item TEXT PRIMARY KEY,
    quantity REAL NOT NULL DEFAULT 0
);
"""

INVENTORY_COLUMNS = ["item", "current_stock"]


def initialize_inventory_table(db_path: str | Path | None = None) -> Path:
    """Create the inventory table if needed."""
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(INVENTORY_SCHEMA_SQL)
        connection.commit()

    return path


def add_stock(item: str, quantity: float, db_path: str | Path | None = None) -> float:
    """Increase stock for an item and return the new stock count."""
    return _update_inventory_quantity(item=item, delta=quantity, db_path=db_path)


def remove_stock(item: str, quantity: float, db_path: str | Path | None = None) -> float:
    """Decrease stock for an item and return the new stock count."""
    return _update_inventory_quantity(item=item, delta=-quantity, db_path=db_path)


def get_inventory(db_path: str | Path | None = None) -> pd.DataFrame:
    """Return current inventory stock as a Pandas DataFrame."""
    path = initialize_inventory_table(db_path)

    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT item, quantity
            FROM inventory
            ORDER BY item COLLATE NOCASE ASC
            """
        ).fetchall()

    records: list[dict[str, Any]] = [dict(zip(INVENTORY_COLUMNS, row, strict=True)) for row in rows]
    return pd.DataFrame.from_records(records, columns=INVENTORY_COLUMNS)


def _update_inventory_quantity(item: str, delta: float, db_path: str | Path | None) -> float:
    """Create or update an inventory row by a signed quantity."""
    normalized_item = _normalize_item(item)
    quantity_delta = float(delta)
    path = initialize_inventory_table(db_path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO inventory (item, quantity)
            VALUES (?, ?)
            ON CONFLICT(item) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (normalized_item, quantity_delta),
        )
        row = connection.execute(
            "SELECT quantity FROM inventory WHERE item = ?",
            (normalized_item,),
        ).fetchone()
        connection.commit()

    return float(row[0])


def _normalize_item(item: str) -> str:
    """Normalize item names for stable inventory records."""
    normalized = " ".join((item or "").lower().split()).strip(" ,.-")
    if not normalized:
        raise ValueError("Inventory item is required.")
    return normalized


def _resolve_db_path(db_path: str | Path | None) -> Path:
    """Resolve an explicit or configured database path."""
    if db_path is None:
        return get_database_path()
    return Path(db_path).expanduser()
