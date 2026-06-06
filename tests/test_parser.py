from voiceledger.parser.rules import parse_transaction


def test_parse_sale_with_quantity_and_unit_price() -> None:
    transaction = parse_transaction("Sold 12 mangoes, 20 each")

    assert transaction.transaction_type == "sale"
    assert transaction.quantity == 12
    assert transaction.item == "mangoes"
    assert transaction.unit_price == 20
    assert transaction.amount == 240
    assert transaction.payment_status == "paid"


def test_parse_shorthand_sale() -> None:
    transaction = parse_transaction("mango 12 x 20")

    assert transaction.transaction_type == "sale"
    assert transaction.item == "mango"
    assert transaction.quantity == 12
    assert transaction.unit_price == 20
    assert transaction.amount == 240


def test_parse_expense() -> None:
    transaction = parse_transaction("Paid 500 for supplies")

    assert transaction.transaction_type == "expense"
    assert transaction.amount == 500
    assert transaction.item == "supplies"
    assert transaction.payment_status == "paid"


def test_parse_shorthand_expense() -> None:
    transaction = parse_transaction("rent 300")

    assert transaction.transaction_type == "expense"
    assert transaction.item == "rent"
    assert transaction.amount == 300


def test_parse_inventory_purchase() -> None:
    transaction = parse_transaction("Bought 50 mangoes")

    assert transaction.transaction_type == "inventory_purchase"
    assert transaction.quantity == 50
    assert transaction.item == "mangoes"
    assert transaction.payment_status == "paid"


def test_parse_sale_without_unit_price_for_inventory() -> None:
    transaction = parse_transaction("Sold 12 mangoes")

    assert transaction.transaction_type == "sale"
    assert transaction.quantity == 12
    assert transaction.item == "mangoes"
    assert transaction.unit_price is None


def test_parse_customer_credit() -> None:
    transaction = parse_transaction("Amit owes 100")

    assert transaction.transaction_type == "customer_credit"
    assert transaction.customer == "Amit"
    assert transaction.amount == 100
    assert transaction.payment_status == "credit"


def test_parse_customer_payment() -> None:
    transaction = parse_transaction("Amit paid 50")

    assert transaction.transaction_type == "customer_payment"
    assert transaction.customer == "Amit"
    assert transaction.amount == 50
    assert transaction.payment_status == "paid"


def test_unknown_note_is_preserved() -> None:
    transaction = parse_transaction("Need to check yesterday")

    assert transaction.transaction_type == "unknown"
    assert transaction.notes == "Need to check yesterday"
