from pathlib import Path

from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.database import add_transaction, get_transactions, initialize_database
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
