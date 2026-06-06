"""Bulk note parsing helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from voiceledger.parser.rules import parse_transaction
from voiceledger.parser.schema import Transaction


REVIEW_COLUMNS = [
    "transaction_type",
    "item",
    "quantity",
    "unit_price",
    "amount",
    "customer",
    "payment_status",
    "notes",
    "confidence",
]


def parse_bulk_notes(notes: str, parser: Callable[[str], Transaction] = parse_transaction) -> pd.DataFrame:
    """Split pasted notes into lines and parse each line for review."""
    transactions = [parser(line) for line in _split_note_lines(notes)]
    return transactions_to_dataframe(transactions)


def transactions_to_dataframe(transactions: list[Transaction]) -> pd.DataFrame:
    """Convert transactions into an editable review DataFrame."""
    records = [transaction.model_dump() for transaction in transactions]
    return pd.DataFrame.from_records(records, columns=REVIEW_COLUMNS)


def review_table_to_transactions(review_table: Any) -> list[Transaction]:
    """Convert an edited review table back into validated transactions."""
    frame = _coerce_review_table(review_table)
    transactions: list[Transaction] = []

    for record in frame.to_dict(orient="records"):
        cleaned = _clean_record(record)
        if _is_empty_record(cleaned):
            continue
        transactions.append(Transaction(**cleaned))

    return transactions


def _split_note_lines(notes: str) -> list[str]:
    """Return non-empty stripped lines from pasted notes."""
    return [line.strip() for line in (notes or "").splitlines() if line.strip()]


def _coerce_review_table(review_table: Any) -> pd.DataFrame:
    """Coerce common Gradio Dataframe values into a Pandas DataFrame."""
    if review_table is None:
        return pd.DataFrame(columns=REVIEW_COLUMNS)
    if isinstance(review_table, pd.DataFrame):
        return review_table.reindex(columns=REVIEW_COLUMNS)
    if isinstance(review_table, list):
        return pd.DataFrame(review_table, columns=REVIEW_COLUMNS)
    if isinstance(review_table, dict) and "data" in review_table:
        headers = review_table.get("headers") or REVIEW_COLUMNS
        return pd.DataFrame(review_table["data"], columns=headers).reindex(columns=REVIEW_COLUMNS)
    return pd.DataFrame(review_table).reindex(columns=REVIEW_COLUMNS)


def _clean_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize editable table values before Pydantic validation."""
    cleaned = dict(record)
    for field in ["item", "customer", "notes"]:
        cleaned[field] = _none_if_blank(cleaned.get(field))

    for field in ["quantity", "unit_price", "amount", "confidence"]:
        cleaned[field] = _number_or_none(cleaned.get(field))

    cleaned["transaction_type"] = _none_if_blank(cleaned.get("transaction_type")) or "unknown"
    cleaned["payment_status"] = _none_if_blank(cleaned.get("payment_status")) or "unknown"
    cleaned["notes"] = cleaned["notes"] or ""
    cleaned["confidence"] = cleaned["confidence"] if cleaned["confidence"] is not None else 0.0
    return cleaned


def _none_if_blank(value: Any) -> Any:
    """Return None for blank, null, or NaN values."""
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def _number_or_none(value: Any) -> float | None:
    """Return a float for numeric values, otherwise None."""
    normalized = _none_if_blank(value)
    if normalized is None:
        return None
    return float(normalized)


def _is_empty_record(record: dict[str, Any]) -> bool:
    """Return whether a review row has no meaningful transaction data."""
    return (
        record["transaction_type"] == "unknown"
        and record["item"] is None
        and record["amount"] is None
        and record["customer"] is None
        and not record["notes"]
    )
