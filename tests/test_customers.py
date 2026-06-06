from pathlib import Path

from voiceledger.ledger.customers import add_credit, get_customer_balances, record_payment


def test_add_credit_creates_customer_balance(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    new_balance = add_credit("amit", 100, db_path)
    balances = get_customer_balances(db_path)

    assert new_balance == 100
    assert len(balances) == 1
    assert balances.iloc[0]["customer"] == "Amit"
    assert balances.iloc[0]["outstanding_balance"] == 100


def test_record_payment_decreases_customer_balance(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_credit("Amit", 100, db_path)
    new_balance = record_payment("Amit", 50, db_path)
    balances = get_customer_balances(db_path)

    assert new_balance == 50
    assert balances.iloc[0]["outstanding_balance"] == 50
