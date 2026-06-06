from datetime import date
from pathlib import Path

import pytest

from voiceledger.ledger.database import add_transaction
from voiceledger.parser.rules import parse_transaction
from voiceledger.reports.pdf_report import build_daily_summary, generate_daily_summary_pdf


def test_build_daily_summary_includes_financial_credit_and_inventory_data(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Bought 50 mangoes for 200"), db_path)
    add_transaction(parse_transaction("Sold 12 mangoes, 20 each"), db_path)
    add_transaction(parse_transaction("Paid 100 for supplies"), db_path)
    add_transaction(parse_transaction("Amit owes 100"), db_path)

    summary = build_daily_summary(db_path=db_path, report_date=date.today())

    assert summary.total_sales == 240
    assert summary.total_expenses == 300
    assert summary.net_profit == -60
    assert summary.customer_credit_outstanding == 100
    assert len(summary.inventory) == 1
    assert summary.inventory.iloc[0]["item"] == "mangoes"
    assert summary.inventory.iloc[0]["current_stock"] == 38


def test_generate_daily_summary_pdf_creates_file(tmp_path: Path) -> None:
    pytest.importorskip("fpdf")
    db_path = tmp_path / "voiceledger.sqlite3"
    add_transaction(parse_transaction("Sold 12 mangoes, 20 each"), db_path)

    report_path = generate_daily_summary_pdf(db_path=db_path, output_dir=tmp_path)

    assert report_path.exists()
    assert report_path.suffix == ".pdf"
    assert report_path.stat().st_size > 0
