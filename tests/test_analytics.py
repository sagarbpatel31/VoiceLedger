from pathlib import Path

from voiceledger.ledger.analytics import (
    calculate_daily_expenses,
    calculate_daily_sales,
    calculate_net_profit,
    low_stock_items,
    outstanding_credit,
    top_selling_items,
)
from voiceledger.ledger.database import add_transaction
from voiceledger.parser.rules import parse_transaction


def test_calculate_daily_sales_expenses_and_net_profit(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Bought 50 mangoes for 200"), db_path)
    add_transaction(parse_transaction("Sold 12 mangoes, 20 each"), db_path)
    add_transaction(parse_transaction("Paid 100 for supplies"), db_path)

    assert calculate_daily_sales(db_path) == 240
    assert calculate_daily_expenses(db_path) == 300
    assert calculate_net_profit(db_path) == -60


def test_top_selling_items_orders_by_quantity(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Sold 12 mangoes, 20 each"), db_path)
    add_transaction(parse_transaction("Sold 5 bananas, 10 each"), db_path)
    add_transaction(parse_transaction("Sold 3 mangoes, 20 each"), db_path)

    top_items = top_selling_items(db_path)

    assert len(top_items) == 2
    assert top_items.iloc[0]["item"] == "mangoes"
    assert top_items.iloc[0]["quantity_sold"] == 15
    assert top_items.iloc[0]["sales_amount"] == 300


def test_outstanding_credit_totals_customer_balances(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Amit owes 100"), db_path)
    add_transaction(parse_transaction("Amit paid 25"), db_path)

    assert outstanding_credit(db_path) == 75


def test_low_stock_items_returns_items_below_threshold(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Bought 10 mangoes"), db_path)
    add_transaction(parse_transaction("Sold 6 mangoes"), db_path)
    add_transaction(parse_transaction("Bought 20 bananas"), db_path)

    low_stock = low_stock_items(db_path, threshold=5)

    assert len(low_stock) == 1
    assert low_stock.iloc[0]["item"] == "mangoes"
    assert low_stock.iloc[0]["current_stock"] == 4
