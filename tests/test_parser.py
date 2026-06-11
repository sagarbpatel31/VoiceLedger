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


def test_parse_quantity_first_sale() -> None:
    transaction = parse_transaction("12 mango 20 each")

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


def test_parse_hinglish_expense() -> None:
    transaction = parse_transaction("rent 300 diya")

    assert transaction.transaction_type == "expense"
    assert transaction.item == "rent"
    assert transaction.amount == 300


def test_parse_inventory_purchase() -> None:
    transaction = parse_transaction("Bought 50 mangoes")

    assert transaction.transaction_type == "inventory_purchase"
    assert transaction.quantity == 50
    assert transaction.item == "mangoes"
    assert transaction.payment_status == "paid"


def test_parse_quantity_first_inventory_purchase() -> None:
    transaction = parse_transaction("50 mango kharida")

    assert transaction.transaction_type == "inventory_purchase"
    assert transaction.quantity == 50
    assert transaction.item == "mango"


def test_parse_gujarati_lite_inventory_purchase() -> None:
    transaction = parse_transaction("50 mango lidha")

    assert transaction.transaction_type == "inventory_purchase"
    assert transaction.quantity == 50
    assert transaction.item == "mango"


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


def test_parse_hinglish_customer_credit() -> None:
    transaction = parse_transaction("Amit ne 100 dene hai")

    assert transaction.transaction_type == "customer_credit"
    assert transaction.customer == "Amit"
    assert transaction.amount == 100


def test_parse_customer_payment() -> None:
    transaction = parse_transaction("Amit paid 50")

    assert transaction.transaction_type == "customer_payment"
    assert transaction.customer == "Amit"
    assert transaction.amount == 50
    assert transaction.payment_status == "paid"


def test_parse_hinglish_customer_payment() -> None:
    transaction = parse_transaction("Amit ne 50 diya")

    assert transaction.transaction_type == "customer_payment"
    assert transaction.customer == "Amit"
    assert transaction.amount == 50


def test_parse_spanish_seller_phrases() -> None:
    sale = parse_transaction("Vendí 12 mangos, 20 cada uno")
    expense = parse_transaction("Pagué 500 por suministros")
    credit = parse_transaction("Amit debe 100")
    payment = parse_transaction("Amit pagó 50")
    stock = parse_transaction("Compré 50 mangos")

    assert sale.transaction_type == "sale"
    assert sale.amount == 240
    assert expense.transaction_type == "expense"
    assert expense.amount == 500
    assert credit.transaction_type == "customer_credit"
    assert credit.amount == 100
    assert payment.transaction_type == "customer_payment"
    assert payment.amount == 50
    assert stock.transaction_type == "inventory_purchase"
    assert stock.quantity == 50


def test_parse_french_seller_phrases() -> None:
    sale = parse_transaction("Vendu 12 mangues, 20 chacun")
    expense = parse_transaction("Payé 500 pour fournitures")
    credit = parse_transaction("Amit doit 100")
    payment = parse_transaction("Amit a payé 50")
    stock = parse_transaction("Acheté 50 mangues")

    assert sale.transaction_type == "sale"
    assert sale.amount == 240
    assert expense.transaction_type == "expense"
    assert expense.amount == 500
    assert credit.transaction_type == "customer_credit"
    assert credit.amount == 100
    assert payment.transaction_type == "customer_payment"
    assert payment.amount == 50
    assert stock.transaction_type == "inventory_purchase"
    assert stock.quantity == 50


def test_parse_portuguese_seller_phrases() -> None:
    sale = parse_transaction("Vendi 12 mangas, 20 cada")
    expense = parse_transaction("Paguei 500 por suprimentos")
    credit = parse_transaction("Amit deve 100")
    payment = parse_transaction("Amit pagou 50")
    stock = parse_transaction("Comprei 50 mangas")

    assert sale.transaction_type == "sale"
    assert sale.amount == 240
    assert expense.transaction_type == "expense"
    assert expense.amount == 500
    assert credit.transaction_type == "customer_credit"
    assert credit.amount == 100
    assert payment.transaction_type == "customer_payment"
    assert payment.amount == 50
    assert stock.transaction_type == "inventory_purchase"
    assert stock.quantity == 50


def test_unknown_note_is_preserved() -> None:
    transaction = parse_transaction("Need to check yesterday")

    assert transaction.transaction_type == "unknown"
    assert transaction.notes == "Need to check yesterday"
