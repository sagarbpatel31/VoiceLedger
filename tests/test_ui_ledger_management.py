from pathlib import Path

import pytest

pytest.importorskip("gradio")

from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.database import add_transaction, get_transactions
from voiceledger.ledger.inventory import get_inventory
from voiceledger.parser.rules import parse_transaction
from voiceledger.ui import gradio_app


def test_load_transaction_for_edit_returns_form_values(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    transaction_id = add_transaction(parse_transaction("Sold 12 mangoes, 20 each"), db_path)

    values = gradio_app._load_transaction_for_edit(transaction_id, db_path)

    assert values[0] == "sale"
    assert values[1] == "mangoes"
    assert values[2] == 12
    assert values[4] == 240
    assert "Loaded transaction" in values[-1]


def test_update_transaction_and_refresh_updates_dependent_views(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    add_transaction(parse_transaction("Bought 50 mangoes"), db_path)
    sale_id = add_transaction(parse_transaction("Sold 12 mangoes"), db_path)

    result = gradio_app._update_transaction_and_refresh(
        sale_id,
        "sale",
        "mangoes",
        20,
        None,
        None,
        None,
        "paid",
        "Sold 20 mangoes",
        0.9,
        db_path,
    )

    assert "Updated transaction" in result[0]
    inventory = get_inventory(db_path)
    assert inventory.iloc[0]["current_stock"] == 30


def test_delete_transaction_and_refresh_updates_dependent_views(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    add_transaction(parse_transaction("Amit owes 100"), db_path)
    payment_id = add_transaction(parse_transaction("Amit paid 50"), db_path)

    result = gradio_app._delete_transaction_and_refresh(payment_id, db_path)

    assert "Deleted transaction" in result[0]
    balances = get_customer_balances(db_path)
    assert balances.iloc[0]["outstanding_balance"] == 100


def test_export_ledger_csv_returns_file_path(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    add_transaction(parse_transaction("Paid 500 for supplies"), db_path)

    file_path, status = gradio_app._export_ledger_csv(db_path)

    assert Path(file_path).exists()
    assert "CSV is ready" in status


def test_seed_demo_transactions_adds_realistic_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    result = gradio_app._seed_demo_transactions_and_refresh(db_path)
    ledger = get_transactions(db_path)

    assert "Seeded" in result[0]
    assert len(ledger) == len(gradio_app.DEMO_NOTES)
