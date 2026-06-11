"""Action-oriented seller messages for follow-up and restocking."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.inventory import get_inventory
from voiceledger.ledger.settings import get_business_settings, get_low_stock_threshold


REORDER_COLUMNS = ["item", "current_stock", "suggested_action"]


def generate_customer_followup(customer_name: str, db_path: str | Path | None = None) -> str:
    """Generate a short WhatsApp reminder for one customer's outstanding balance."""
    name = " ".join((customer_name or "").split()).strip()
    if not name:
        return "Select a customer to generate a follow-up message."

    settings = get_business_settings(db_path)
    currency = settings["currency_symbol"]
    balances = get_customer_balances(db_path)
    if balances.empty:
        return f"No outstanding balance found for {name}."

    matches = balances[balances["customer"].astype(str).str.lower() == name.lower()]
    if matches.empty:
        return f"No outstanding balance found for {name}."

    balance = float(matches.iloc[0]["outstanding_balance"])
    if balance <= 0:
        return f"Hi {matches.iloc[0]['customer']}, your balance is clear. Thank you."

    return f"Hi {matches.iloc[0]['customer']}, your balance is {_format_money(balance, currency)}. Please pay when possible."


def generate_reorder_list(db_path: str | Path | None = None) -> tuple[pd.DataFrame, str]:
    """Return low-stock rows and a WhatsApp-ready restock message."""
    settings = get_business_settings(db_path)
    threshold = get_low_stock_threshold(db_path)
    inventory = get_inventory(db_path)
    if inventory.empty:
        return pd.DataFrame(columns=REORDER_COLUMNS), "No inventory recorded yet."

    stock = inventory.copy()
    stock["current_stock"] = pd.to_numeric(stock["current_stock"], errors="coerce").fillna(0)
    low_stock = stock[stock["current_stock"] < threshold].sort_values(["current_stock", "item"]).copy()
    if low_stock.empty:
        return pd.DataFrame(columns=REORDER_COLUMNS), f"All stock is above the low-stock threshold of {_format_quantity(threshold)}."

    low_stock["suggested_action"] = low_stock.apply(
        lambda row: f"Restock {row['item']} soon; current stock is {_format_quantity(row['current_stock'])}.",
        axis=1,
    )
    message_lines = [
        f"{settings['business_name']} Reorder List",
        f"Low-stock threshold: {_format_quantity(threshold)}",
        "",
    ]
    message_lines.extend(
        f"- {row['item'].title()}: {_format_quantity(row['current_stock'])} left"
        for _, row in low_stock.head(8).iterrows()
    )
    return low_stock[REORDER_COLUMNS].reset_index(drop=True), "\n".join(message_lines)


def _format_quantity(value: object) -> str:
    """Format quantity without unnecessary decimals."""
    quantity = float(value)
    if quantity.is_integer():
        return str(int(quantity))
    return f"{quantity:.2f}"


def _format_money(value: float, currency_symbol: str) -> str:
    """Format money with the configured currency symbol."""
    amount = float(value)
    if amount.is_integer():
        return f"{currency_symbol}{int(amount)}"
    return f"{currency_symbol}{amount:,.2f}"
