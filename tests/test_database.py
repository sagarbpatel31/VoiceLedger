from pathlib import Path

from voiceledger.ledger.database import add_transaction, get_transactions, initialize_database
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
