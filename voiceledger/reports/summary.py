"""Simple report summaries for saved transactions."""

from __future__ import annotations

import pandas as pd


def summarize_transactions(transactions: pd.DataFrame) -> dict[str, float]:
    """Return basic totals by transaction type."""
    if transactions.empty or "transaction_type" not in transactions or "amount" not in transactions:
        return {"sales": 0.0, "expenses": 0.0, "customer_credit": 0.0}

    amount_by_type = transactions.groupby("transaction_type")["amount"].sum(numeric_only=True)
    return {
        "sales": float(amount_by_type.get("sale", 0.0)),
        "expenses": float(amount_by_type.get("expense", 0.0)),
        "customer_credit": float(amount_by_type.get("customer_credit", 0.0)),
    }
