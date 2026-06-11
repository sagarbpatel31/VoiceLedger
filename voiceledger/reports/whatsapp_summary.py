"""WhatsApp-friendly business summary generation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from voiceledger.ledger.analytics import (
    calculate_daily_expenses,
    calculate_daily_sales,
    calculate_net_profit,
    low_stock_items,
    outstanding_credit,
    top_selling_items,
)


def generate_whatsapp_summary(
    db_path: str | Path | None = None,
    report_date: date | None = None,
    low_stock_threshold: float = 5,
    business_name: str = "VoiceLedger",
    currency_symbol: str = "₹",
) -> str:
    """Generate a concise daily summary suitable for WhatsApp sharing."""
    sales = calculate_daily_sales(db_path=db_path, report_date=report_date)
    expenses = calculate_daily_expenses(db_path=db_path, report_date=report_date)
    profit = calculate_net_profit(db_path=db_path, report_date=report_date)
    credit = outstanding_credit(db_path=db_path)
    top_product = _top_product_name(top_selling_items(db_path=db_path, report_date=report_date, limit=1))
    low_stock = _low_stock_names(low_stock_items(db_path=db_path, threshold=low_stock_threshold))

    return "\n".join(
        [
            f"{business_name} Daily Summary",
            "",
            f"Sales: {_format_money(sales, currency_symbol)}",
            f"Expenses: {_format_money(expenses, currency_symbol)}",
            f"Profit: {_format_money(profit, currency_symbol)}",
            "",
            f"Outstanding Credit: {_format_money(credit, currency_symbol)}",
            "",
            f"Top Product: {top_product}",
            f"Low Stock: {low_stock}",
        ]
    )


def _top_product_name(top_items: pd.DataFrame) -> str:
    """Return the top selling item name for display."""
    if top_items.empty:
        return "None"
    return str(top_items.iloc[0]["item"]).title()


def _low_stock_names(low_stock: pd.DataFrame) -> str:
    """Return a compact low-stock item list for display."""
    if low_stock.empty:
        return "None"
    return ", ".join(str(item).title() for item in low_stock["item"].head(3))


def _format_money(value: float, currency_symbol: str) -> str:
    """Format an amount using a rupee symbol and no decimals for whole values."""
    amount = float(value)
    if amount.is_integer():
        return f"{currency_symbol}{int(amount)}"
    return f"{currency_symbol}{amount:,.2f}"
