"""PDF report generation for VoiceLedger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from tempfile import gettempdir

import pandas as pd

from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.database import get_transactions
from voiceledger.ledger.inventory import get_inventory


@dataclass(frozen=True)
class DailySummary:
    """Computed values for a daily business summary."""

    report_date: date
    total_sales: float
    total_expenses: float
    net_profit: float
    customer_credit_outstanding: float
    inventory: pd.DataFrame


def build_daily_summary(db_path: str | Path | None = None, report_date: date | None = None) -> DailySummary:
    """Build a daily summary from saved ledger, customer, and inventory data."""
    selected_date = report_date or date.today()
    transactions = _filter_transactions_for_date(get_transactions(db_path), selected_date)
    customer_balances = get_customer_balances(db_path)
    inventory = get_inventory(db_path)

    total_sales = _sum_amounts(transactions, ["sale"])
    total_expenses = _sum_amounts(transactions, ["expense", "inventory_purchase"])
    customer_credit_outstanding = _sum_column(customer_balances, "outstanding_balance")

    return DailySummary(
        report_date=selected_date,
        total_sales=total_sales,
        total_expenses=total_expenses,
        net_profit=round(total_sales - total_expenses, 2),
        customer_credit_outstanding=customer_credit_outstanding,
        inventory=inventory,
    )


def generate_daily_summary_pdf(
    db_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    report_date: date | None = None,
    business_name: str = "VoiceLedger",
    currency_symbol: str = "",
) -> Path:
    """Generate a Daily Summary PDF and return its filesystem path."""
    try:
        from fpdf import FPDF
    except ImportError as exc:  # pragma: no cover - environment dependent.
        raise RuntimeError("fpdf2 is not installed. Install dependencies from requirements.txt.") from exc

    summary = build_daily_summary(db_path=db_path, report_date=report_date)
    output_path = _build_output_path(output_dir, summary.report_date)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    _add_title(pdf, summary.report_date, business_name)
    _add_totals(pdf, summary, currency_symbol)
    _add_inventory_summary(pdf, summary.inventory)

    pdf.output(str(output_path))
    return output_path


def _filter_transactions_for_date(transactions: pd.DataFrame, selected_date: date) -> pd.DataFrame:
    """Return only transactions created on the selected date."""
    if transactions.empty or "created_at" not in transactions:
        return transactions

    created_dates = pd.to_datetime(transactions["created_at"], errors="coerce").dt.date
    return transactions.loc[created_dates == selected_date].copy()


def _sum_amounts(transactions: pd.DataFrame, transaction_types: list[str]) -> float:
    """Sum transaction amounts for the requested transaction types."""
    if transactions.empty or "transaction_type" not in transactions or "amount" not in transactions:
        return 0.0

    filtered = transactions[transactions["transaction_type"].isin(transaction_types)]
    return _sum_column(filtered, "amount")


def _sum_column(frame: pd.DataFrame, column: str) -> float:
    """Safely sum a numeric DataFrame column."""
    if frame.empty or column not in frame:
        return 0.0
    return round(float(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum()), 2)


def _build_output_path(output_dir: str | Path | None, report_date: date) -> Path:
    """Return a stable temporary output path for the PDF report."""
    directory = Path(output_dir) if output_dir is not None else Path(gettempdir()) / "voiceledger-reports"
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%H%M%S")
    return directory / f"voiceledger-daily-summary-{report_date.isoformat()}-{timestamp}.pdf"


def _add_title(pdf: object, report_date: date, business_name: str) -> None:
    """Add report title and date."""
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, f"{_pdf_safe_text(business_name)} Daily Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Date: {report_date.isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def _add_totals(pdf: object, summary: DailySummary, currency_symbol: str) -> None:
    """Add the financial summary section."""
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Financial Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    _add_metric_row(pdf, "Total Sales", summary.total_sales, currency_symbol)
    _add_metric_row(pdf, "Total Expenses", summary.total_expenses, currency_symbol)
    _add_metric_row(pdf, "Net Profit", summary.net_profit, currency_symbol)
    _add_metric_row(pdf, "Customer Credit Outstanding", summary.customer_credit_outstanding, currency_symbol)
    pdf.ln(5)


def _add_metric_row(pdf: object, label: str, value: float, currency_symbol: str) -> None:
    """Add one label/value row to the PDF."""
    pdf.cell(85, 8, label)
    pdf.cell(0, 8, _format_money(value, currency_symbol), new_x="LMARGIN", new_y="NEXT")


def _add_inventory_summary(pdf: object, inventory: pd.DataFrame) -> None:
    """Add inventory stock rows to the PDF."""
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Inventory Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(110, 8, "Item", border=1)
    pdf.cell(40, 8, "Current Stock", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    if inventory.empty:
        pdf.cell(150, 8, "No inventory recorded.", border=1, new_x="LMARGIN", new_y="NEXT")
        return

    for _, row in inventory.iterrows():
        pdf.cell(110, 8, str(row["item"])[:55], border=1)
        pdf.cell(40, 8, _format_quantity(row["current_stock"]), border=1, new_x="LMARGIN", new_y="NEXT")


def _format_money(value: float, currency_symbol: str) -> str:
    """Format a monetary amount for PDF output."""
    symbol = _pdf_safe_text(currency_symbol)
    return f"{symbol}{value:,.2f}" if symbol else f"{value:,.2f}"


def _format_quantity(value: object) -> str:
    """Format inventory quantities without unnecessary decimal places."""
    quantity = float(value)
    if quantity.is_integer():
        return str(int(quantity))
    return f"{quantity:,.2f}"


def _pdf_safe_text(value: str) -> str:
    """Return text safe for the default fpdf Helvetica font."""
    return str(value or "").replace("₹", "Rs").encode("latin-1", "ignore").decode("latin-1")
