from pathlib import Path

from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.database import (
    add_transaction,
    delete_transaction,
    export_transactions_csv,
    get_transaction,
    get_transactions,
    initialize_database,
    update_transaction,
)
from voiceledger.ledger.inventory import get_inventory
from voiceledger.parser.rules import parse_transaction


def test_initialize_database_creates_file(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    created_path = initialize_database(db_path)

    assert created_path == db_path
    assert db_path.exists()


def test_add_and_get_transactions(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    transaction = parse_transaction("Sold 12 mangoes, 20 each")

    transaction_id = add_transaction(transaction, db_path)
    ledger = get_transactions(db_path)

    assert transaction_id == 1
    assert len(ledger) == 1
    assert ledger.iloc[0]["transaction_type"] == "sale"
    assert ledger.iloc[0]["item"] == "mangoes"
    assert ledger.iloc[0]["amount"] == 240


def test_customer_credit_transaction_updates_balance(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Amit owes 100"), db_path)
    balances = get_customer_balances(db_path)

    assert len(balances) == 1
    assert balances.iloc[0]["customer"] == "Amit"
    assert balances.iloc[0]["outstanding_balance"] == 100


def test_customer_payment_transaction_decreases_balance(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Amit owes 100"), db_path)
    add_transaction(parse_transaction("Amit paid 50"), db_path)
    balances = get_customer_balances(db_path)

    assert len(balances) == 1
    assert balances.iloc[0]["customer"] == "Amit"
    assert balances.iloc[0]["outstanding_balance"] == 50


def test_inventory_purchase_transaction_increases_stock(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Bought 50 mangoes"), db_path)
    inventory = get_inventory(db_path)

    assert len(inventory) == 1
    assert inventory.iloc[0]["item"] == "mangoes"
    assert inventory.iloc[0]["current_stock"] == 50


def test_sale_transaction_decreases_stock(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Bought 50 mangoes"), db_path)
    add_transaction(parse_transaction("Sold 12 mangoes"), db_path)
    inventory = get_inventory(db_path)

    assert len(inventory) == 1
    assert inventory.iloc[0]["item"] == "mangoes"
    assert inventory.iloc[0]["current_stock"] == 38


def test_get_transaction_returns_saved_transaction(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    transaction_id = add_transaction(parse_transaction("Paid 500 for supplies"), db_path)

    transaction = get_transaction(transaction_id, db_path)

    assert transaction is not None
    assert transaction.transaction_type == "expense"
    assert transaction.amount == 500


def test_update_sale_rebuilds_inventory(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    add_transaction(parse_transaction("Bought 50 mangoes"), db_path)
    sale_id = add_transaction(parse_transaction("Sold 12 mangoes"), db_path)

    updated = update_transaction(sale_id, parse_transaction("Sold 20 mangoes"), db_path)
    inventory = get_inventory(db_path)

    assert updated is True
    assert inventory.iloc[0]["current_stock"] == 30


def test_delete_sale_rebuilds_inventory(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    add_transaction(parse_transaction("Bought 50 mangoes"), db_path)
    sale_id = add_transaction(parse_transaction("Sold 12 mangoes"), db_path)

    deleted = delete_transaction(sale_id, db_path)
    inventory = get_inventory(db_path)

    assert deleted is True
    assert inventory.iloc[0]["current_stock"] == 50


def test_update_customer_credit_rebuilds_balance(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    credit_id = add_transaction(parse_transaction("Amit owes 100"), db_path)
    add_transaction(parse_transaction("Amit paid 50"), db_path)

    updated = update_transaction(credit_id, parse_transaction("Amit owes 200"), db_path)
    balances = get_customer_balances(db_path)

    assert updated is True
    assert balances.iloc[0]["outstanding_balance"] == 150


def test_delete_customer_payment_rebuilds_balance(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    add_transaction(parse_transaction("Amit owes 100"), db_path)
    payment_id = add_transaction(parse_transaction("Amit paid 50"), db_path)

    deleted = delete_transaction(payment_id, db_path)
    balances = get_customer_balances(db_path)

    assert deleted is True
    assert balances.iloc[0]["outstanding_balance"] == 100


def test_export_transactions_csv_includes_ledger_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    export_path = tmp_path / "transactions.csv"
    add_transaction(parse_transaction("Sold 12 mangoes, 20 each"), db_path)

    result_path = export_transactions_csv(db_path, export_path)
    csv_text = result_path.read_text()

    assert result_path == export_path
    assert "id,transaction_type,item,quantity,unit_price,amount,customer,payment_status,notes,confidence,created_at" in csv_text
    assert "sale,mangoes" in csv_text
