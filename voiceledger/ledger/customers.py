"""Customer credit balance persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from voiceledger.config import get_database_path


CUSTOMERS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    balance REAL NOT NULL DEFAULT 0
);
"""

CUSTOMER_BALANCE_COLUMNS = ["customer", "outstanding_balance"]


def initialize_customers_table(db_path: str | Path | None = None) -> Path:
    """Create the customers table if needed."""
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(CUSTOMERS_SCHEMA_SQL)
        connection.commit()

    return path


def add_credit(name: str, amount: float, db_path: str | Path | None = None) -> float:
    """Increase a customer's outstanding balance and return the new balance."""
    return _update_customer_balance(name=name, delta=amount, db_path=db_path)


def record_payment(name: str, amount: float, db_path: str | Path | None = None) -> float:
    """Decrease a customer's outstanding balance and return the new balance."""
    return _update_customer_balance(name=name, delta=-amount, db_path=db_path)


def get_customer_balances(db_path: str | Path | None = None) -> pd.DataFrame:
    """Return customer balances as a Pandas DataFrame."""
    path = initialize_customers_table(db_path)

    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT name, balance
            FROM customers
            WHERE balance != 0
            ORDER BY name COLLATE NOCASE ASC
            """
        ).fetchall()

    records: list[dict[str, Any]] = [
        dict(zip(CUSTOMER_BALANCE_COLUMNS, row, strict=True)) for row in rows
    ]
    return pd.DataFrame.from_records(records, columns=CUSTOMER_BALANCE_COLUMNS)


def _update_customer_balance(name: str, delta: float, db_path: str | Path | None) -> float:
    """Create or update a customer's balance by a signed amount."""
    customer_name = _normalize_customer_name(name)
    amount_delta = float(delta)
    path = initialize_customers_table(db_path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO customers (name, balance)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET balance = balance + excluded.balance
            """,
            (customer_name, amount_delta),
        )
        row = connection.execute(
            "SELECT balance FROM customers WHERE name = ?",
            (customer_name,),
        ).fetchone()
        connection.commit()

    return float(row[0])


def _normalize_customer_name(name: str) -> str:
    """Normalize customer names for stable balance records."""
    normalized = " ".join((name or "").split()).strip()
    if not normalized:
        raise ValueError("Customer name is required.")
    return " ".join(part.capitalize() for part in normalized.split())


def _resolve_db_path(db_path: str | Path | None) -> Path:
    """Resolve an explicit or configured database path."""
    if db_path is None:
        return get_database_path()
    return Path(db_path).expanduser()
