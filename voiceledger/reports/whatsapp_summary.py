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
    language: str = "English",
) -> str:
    """Generate a concise daily summary suitable for WhatsApp sharing."""
    labels = _summary_labels(language)
    sales = calculate_daily_sales(db_path=db_path, report_date=report_date)
    expenses = calculate_daily_expenses(db_path=db_path, report_date=report_date)
    profit = calculate_net_profit(db_path=db_path, report_date=report_date)
    credit = outstanding_credit(db_path=db_path)
    top_product = _top_product_name(top_selling_items(db_path=db_path, report_date=report_date, limit=1))
    low_stock = _low_stock_names(low_stock_items(db_path=db_path, threshold=low_stock_threshold))

    return "\n".join(
        [
            f"{business_name} {labels['daily_summary']}",
            "",
            f"{labels['sales']}: {_format_money(sales, currency_symbol)}",
            f"{labels['expenses']}: {_format_money(expenses, currency_symbol)}",
            f"{labels['profit']}: {_format_money(profit, currency_symbol)}",
            "",
            f"{labels['outstanding_credit']}: {_format_money(credit, currency_symbol)}",
            "",
            f"{labels['top_product']}: {top_product}",
            f"{labels['low_stock']}: {low_stock}",
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


def _summary_labels(language: str) -> dict[str, str]:
    """Return localized labels for a WhatsApp daily summary."""
    normalized = (language or "English").strip().lower()
    labels = {
        "english": {
            "daily_summary": "Daily Summary",
            "sales": "Sales",
            "expenses": "Expenses",
            "profit": "Profit",
            "outstanding_credit": "Outstanding Credit",
            "top_product": "Top Product",
            "low_stock": "Low Stock",
        },
        "spanish": {
            "daily_summary": "Resumen Diario",
            "sales": "Ventas",
            "expenses": "Gastos",
            "profit": "Ganancia",
            "outstanding_credit": "Credito Pendiente",
            "top_product": "Producto Principal",
            "low_stock": "Bajo Stock",
        },
        "french": {
            "daily_summary": "Resume Quotidien",
            "sales": "Ventes",
            "expenses": "Depenses",
            "profit": "Profit",
            "outstanding_credit": "Credit En Attente",
            "top_product": "Meilleur Produit",
            "low_stock": "Stock Bas",
        },
        "portuguese": {
            "daily_summary": "Resumo Diario",
            "sales": "Vendas",
            "expenses": "Despesas",
            "profit": "Lucro",
            "outstanding_credit": "Credito Pendente",
            "top_product": "Produto Principal",
            "low_stock": "Estoque Baixo",
        },
    }
    return labels.get(normalized, labels["english"])
