"""Business analytics helpers for VoiceLedger."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.database import get_transactions
from voiceledger.ledger.inventory import get_inventory


DEFAULT_LOW_STOCK_THRESHOLD = 5


def calculate_daily_sales(db_path: str | Path | None = None, report_date: date | None = None) -> float:
    """Return total sales for the selected day."""
    transactions = _transactions_for_date(db_path, report_date)
    return _sum_amounts(transactions, ["sale"])


def calculate_daily_expenses(db_path: str | Path | None = None, report_date: date | None = None) -> float:
    """Return total expenses for the selected day."""
    transactions = _transactions_for_date(db_path, report_date)
    return _sum_amounts(transactions, ["expense", "inventory_purchase"])


def calculate_net_profit(db_path: str | Path | None = None, report_date: date | None = None) -> float:
    """Return sales minus expenses for the selected day."""
    sales = calculate_daily_sales(db_path=db_path, report_date=report_date)
    expenses = calculate_daily_expenses(db_path=db_path, report_date=report_date)
    return round(sales - expenses, 2)


def top_selling_items(
    db_path: str | Path | None = None,
    report_date: date | None = None,
    limit: int = 5,
) -> pd.DataFrame:
    """Return top selling items by sold quantity for the selected day."""
    transactions = _transactions_for_date(db_path, report_date)
    if transactions.empty:
        return _empty_top_items_frame()

    sales = transactions[
        (transactions["transaction_type"] == "sale")
        & transactions["item"].notna()
        & transactions["quantity"].notna()
    ].copy()
    if sales.empty:
        return _empty_top_items_frame()

    sales["quantity"] = pd.to_numeric(sales["quantity"], errors="coerce").fillna(0)
    sales["amount"] = pd.to_numeric(sales["amount"], errors="coerce").fillna(0)
    grouped = (
        sales.groupby("item", as_index=False)
        .agg(quantity_sold=("quantity", "sum"), sales_amount=("amount", "sum"))
        .sort_values(["quantity_sold", "sales_amount"], ascending=[False, False])
        .head(limit)
    )
    return grouped.reset_index(drop=True)


def outstanding_credit(db_path: str | Path | None = None) -> float:
    """Return total outstanding customer credit."""
    balances = get_customer_balances(db_path)
    if balances.empty or "outstanding_balance" not in balances:
        return 0.0
    total = pd.to_numeric(balances["outstanding_balance"], errors="coerce").fillna(0).sum()
    return round(float(total), 2)


def low_stock_items(
    db_path: str | Path | None = None,
    threshold: float = DEFAULT_LOW_STOCK_THRESHOLD,
) -> pd.DataFrame:
    """Return inventory rows where current stock is below the threshold."""
    inventory = get_inventory(db_path)
    if inventory.empty or "current_stock" not in inventory:
        return pd.DataFrame(columns=["item", "current_stock"])

    stock = inventory.copy()
    stock["current_stock"] = pd.to_numeric(stock["current_stock"], errors="coerce").fillna(0)
    low_stock = stock[stock["current_stock"] < threshold]
    return low_stock.sort_values(["current_stock", "item"], ascending=[True, True]).reset_index(drop=True)


def _transactions_for_date(db_path: str | Path | None, report_date: date | None) -> pd.DataFrame:
    """Return transactions for the selected local date."""
    selected_date = report_date or date.today()
    transactions = get_transactions(db_path)
    if transactions.empty or "created_at" not in transactions:
        return transactions

    created_dates = pd.to_datetime(transactions["created_at"], errors="coerce").dt.date
    return transactions.loc[created_dates == selected_date].copy()


def _sum_amounts(transactions: pd.DataFrame, transaction_types: list[str]) -> float:
    """Sum transaction amounts for selected transaction types."""
    if transactions.empty or "transaction_type" not in transactions or "amount" not in transactions:
        return 0.0

    filtered = transactions[transactions["transaction_type"].isin(transaction_types)]
    if filtered.empty:
        return 0.0

    total = pd.to_numeric(filtered["amount"], errors="coerce").fillna(0).sum()
    return round(float(total), 2)


def _empty_top_items_frame() -> pd.DataFrame:
    """Return an empty top selling items frame with stable columns."""
    return pd.DataFrame(columns=["item", "quantity_sold", "sales_amount"])
