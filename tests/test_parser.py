from voiceledger.parser.rules import parse_transaction


def test_parse_sale_with_quantity_and_unit_price() -> None:
    transaction = parse_transaction("Sold 12 mangoes, 20 each")

    assert transaction.transaction_type == "sale"
    assert transaction.quantity == 12
    assert transaction.item == "mangoes"
    assert transaction.unit_price == 20
    assert transaction.amount == 240
    assert transaction.payment_status == "paid"


def test_parse_expense() -> None:
    transaction = parse_transaction("Paid 500 for supplies")

    assert transaction.transaction_type == "expense"
    assert transaction.amount == 500
    assert transaction.item == "supplies"
    assert transaction.payment_status == "paid"


def test_parse_customer_credit() -> None:
    transaction = parse_transaction("Amit owes 100")

    assert transaction.transaction_type == "customer_credit"
    assert transaction.customer == "Amit"
    assert transaction.amount == 100
    assert transaction.payment_status == "credit"


def test_unknown_note_is_preserved() -> None:
    transaction = parse_transaction("Need to check yesterday")

    assert transaction.transaction_type == "unknown"
    assert transaction.notes == "Need to check yesterday"
