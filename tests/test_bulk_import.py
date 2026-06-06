from pathlib import Path

from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.database import add_transaction, get_transactions
from voiceledger.parser.bulk import parse_bulk_notes, review_table_to_transactions


def test_parse_bulk_notes_splits_lines_and_parses_each_transaction() -> None:
    notes = """
    mango 12 x 20
    rent 300
    Amit owes 100
    Ramesh paid 50
    """

    review_table = parse_bulk_notes(notes)

    assert len(review_table) == 4
    assert review_table.iloc[0]["transaction_type"] == "sale"
    assert review_table.iloc[0]["item"] == "mango"
    assert review_table.iloc[0]["quantity"] == 12
    assert review_table.iloc[0]["unit_price"] == 20
    assert review_table.iloc[0]["amount"] == 240
    assert review_table.iloc[1]["transaction_type"] == "expense"
    assert review_table.iloc[1]["item"] == "rent"
    assert review_table.iloc[1]["amount"] == 300
    assert review_table.iloc[2]["transaction_type"] == "customer_credit"
    assert review_table.iloc[2]["customer"] == "Amit"
    assert review_table.iloc[3]["transaction_type"] == "customer_payment"
    assert review_table.iloc[3]["customer"] == "Ramesh"


def test_review_table_to_transactions_uses_edited_values() -> None:
    review_table = parse_bulk_notes("mango 12 x 20")
    review_table.loc[0, "quantity"] = 10
    review_table.loc[0, "amount"] = 200

    transactions = review_table_to_transactions(review_table)

    assert len(transactions) == 1
    assert transactions[0].quantity == 10
    assert transactions[0].amount == 200


def test_bulk_transactions_save_through_ledger_path(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    review_table = parse_bulk_notes("mango 12 x 20\nAmit owes 100")

    for transaction in review_table_to_transactions(review_table):
        add_transaction(transaction, db_path)

    ledger = get_transactions(db_path)
    balances = get_customer_balances(db_path)

    assert len(ledger) == 2
    assert balances.iloc[0]["customer"] == "Amit"
    assert balances.iloc[0]["outstanding_balance"] == 100
