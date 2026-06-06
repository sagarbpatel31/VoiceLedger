"""SQLite persistence layer for VoiceLedger transactions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from voiceledger.config import get_database_path
from voiceledger.ledger.customers import add_credit, initialize_customers_table, record_payment
from voiceledger.parser.schema import Transaction


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_type TEXT NOT NULL,
    item TEXT,
    quantity REAL,
    unit_price REAL,
    amount REAL,
    customer TEXT,
    payment_status TEXT NOT NULL,
    notes TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

COLUMNS = [
    "id",
    "transaction_type",
    "item",
    "quantity",
    "unit_price",
    "amount",
    "customer",
    "payment_status",
    "notes",
    "confidence",
    "created_at",
]


def initialize_database(db_path: str | Path | None = None) -> Path:
    """Create the SQLite database and transactions table if needed."""
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(SCHEMA_SQL)
        connection.commit()

    initialize_customers_table(path)
    return path


def add_transaction(transaction: Transaction, db_path: str | Path | None = None) -> int:
    """Insert a transaction and return its database id."""
    path = initialize_database(db_path)
    payload = transaction.model_dump()

    with sqlite3.connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO transactions (
                transaction_type,
                item,
                quantity,
                unit_price,
                amount,
                customer,
                payment_status,
                notes,
                confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["transaction_type"],
                payload["item"],
                payload["quantity"],
                payload["unit_price"],
                payload["amount"],
                payload["customer"],
                payload["payment_status"],
                payload["notes"],
                payload["confidence"],
            ),
        )
        connection.commit()
        transaction_id = int(cursor.lastrowid)

    _apply_customer_balance_update(transaction, path)
    return transaction_id


def get_transactions(db_path: str | Path | None = None) -> pd.DataFrame:
    """Return all saved transactions as a Pandas DataFrame."""
    path = initialize_database(db_path)

    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                transaction_type,
                item,
                quantity,
                unit_price,
                amount,
                customer,
                payment_status,
                notes,
                confidence,
                created_at
            FROM transactions
            ORDER BY id DESC
            """
        ).fetchall()

    records: list[dict[str, Any]] = [dict(zip(COLUMNS, row, strict=True)) for row in rows]
    return pd.DataFrame.from_records(records, columns=COLUMNS)


def _resolve_db_path(db_path: str | Path | None) -> Path:
    """Resolve an explicit or configured database path."""
    if db_path is None:
        return get_database_path()
    return Path(db_path).expanduser()


def _apply_customer_balance_update(transaction: Transaction, db_path: Path) -> None:
    """Apply customer balance side effects for credit-related transactions."""
    if not transaction.customer or transaction.amount is None:
        return

    if transaction.transaction_type == "customer_credit":
        add_credit(transaction.customer, transaction.amount, db_path)
    elif transaction.transaction_type == "customer_payment":
        record_payment(transaction.customer, transaction.amount, db_path)
