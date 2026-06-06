"""Rule-based parser for simple bookkeeping notes."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from voiceledger.parser.schema import Transaction


NUMBER_PATTERN = r"(?P<number>\d+(?:\.\d+)?)"
SALE_PATTERN = re.compile(
    rf"\b(?:sold|sell|sale of)\s+"
    rf"(?P<quantity>\d+(?:\.\d+)?)\s+"
    rf"(?P<item>[a-zA-Z][a-zA-Z\s-]*?)"
    rf"(?:,|\s+at|\s+for|\s+@|\s+)?\s*"
    rf"(?P<unit_price>\d+(?:\.\d+)?)?\s*"
    rf"(?:each|per\s+\w+)?\b",
    re.IGNORECASE,
)
EXPENSE_PATTERN = re.compile(
    rf"\b(?:paid|spent)\s+"
    rf"(?P<amount>\d+(?:\.\d+)?)"
    rf"(?:\s+(?:for|on))?\s*"
    rf"(?P<item>[a-zA-Z][a-zA-Z\s-]*)?",
    re.IGNORECASE,
)
INVENTORY_PURCHASE_PATTERN = re.compile(
    rf"\b(?:bought|purchased|buy|stocked|restocked)\s+"
    rf"(?P<quantity>\d+(?:\.\d+)?)\s+"
    rf"(?P<item>[a-zA-Z][a-zA-Z\s-]*?)"
    rf"(?:\s+(?:for|at)\s+(?P<amount>\d+(?:\.\d+)?))?\b",
    re.IGNORECASE,
)
CREDIT_PATTERN = re.compile(
    rf"^\s*(?P<customer>[a-zA-Z][a-zA-Z\s-]*?)\s+"
    rf"(?:owes|owe|will\s+pay|to\s+pay)\s+"
    rf"(?P<amount>\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
CUSTOMER_PAYMENT_PATTERN = re.compile(
    rf"^\s*(?P<customer>[a-zA-Z][a-zA-Z\s-]*?)\s+"
    rf"(?:paid|pays|settled|repaid)\s+"
    rf"(?P<amount>\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


def parse_transaction(note: str) -> Transaction:
    """Parse a text note into a structured transaction.

    The parser is intentionally rule-based for the MVP. It covers sales,
    expenses, and customer credit without calling an LLM.
    """
    cleaned_note = _normalize_note(note)
    if not cleaned_note:
        return Transaction(notes="", confidence=0.0)

    credit = _parse_customer_credit(cleaned_note)
    if credit:
        return credit

    customer_payment = _parse_customer_payment(cleaned_note)
    if customer_payment:
        return customer_payment

    inventory_purchase = _parse_inventory_purchase(cleaned_note)
    if inventory_purchase:
        return inventory_purchase

    sale = _parse_sale(cleaned_note)
    if sale:
        return sale

    expense = _parse_expense(cleaned_note)
    if expense:
        return expense

    return Transaction(notes=cleaned_note, confidence=0.15)


def _parse_sale(note: str) -> Transaction | None:
    """Parse notes like 'Sold 12 mangoes, 20 each'."""
    match = SALE_PATTERN.search(note)
    if not match:
        return None

    quantity = _to_float(match.group("quantity"))
    unit_price = _to_float(match.group("unit_price"))
    item = _clean_item(match.group("item"))
    amount = None
    confidence = 0.72

    if quantity is not None and unit_price is not None:
        amount = round(quantity * unit_price, 2)
        confidence = 0.92

    return Transaction(
        transaction_type="sale",
        item=item,
        quantity=quantity,
        unit_price=unit_price,
        amount=amount,
        payment_status="paid",
        notes=note,
        confidence=confidence,
    )


def _parse_expense(note: str) -> Transaction | None:
    """Parse notes like 'Paid 500 for supplies'."""
    match = EXPENSE_PATTERN.search(note)
    if not match:
        return None

    return Transaction(
        transaction_type="expense",
        item=_clean_item(match.group("item")),
        amount=_to_float(match.group("amount")),
        payment_status="paid",
        notes=note,
        confidence=0.88,
    )


def _parse_inventory_purchase(note: str) -> Transaction | None:
    """Parse notes like 'Bought 50 mangoes'."""
    match = INVENTORY_PURCHASE_PATTERN.search(note)
    if not match:
        return None

    return Transaction(
        transaction_type="inventory_purchase",
        item=_clean_item(match.group("item")),
        quantity=_to_float(match.group("quantity")),
        amount=_to_float(match.group("amount")),
        payment_status="paid",
        notes=note,
        confidence=0.86,
    )


def _parse_customer_credit(note: str) -> Transaction | None:
    """Parse notes like 'Amit owes 100'."""
    match = CREDIT_PATTERN.search(note)
    if not match:
        return None

    return Transaction(
        transaction_type="customer_credit",
        customer=_clean_name(match.group("customer")),
        amount=_to_float(match.group("amount")),
        payment_status="credit",
        notes=note,
        confidence=0.9,
    )


def _parse_customer_payment(note: str) -> Transaction | None:
    """Parse notes like 'Amit paid 50'."""
    match = CUSTOMER_PAYMENT_PATTERN.search(note)
    if not match:
        return None

    return Transaction(
        transaction_type="customer_payment",
        customer=_clean_name(match.group("customer")),
        amount=_to_float(match.group("amount")),
        payment_status="paid",
        notes=note,
        confidence=0.9,
    )


def _normalize_note(note: str) -> str:
    """Normalize user-entered note text for parsing."""
    return re.sub(r"\s+", " ", note or "").strip()


def _clean_item(value: str | None) -> str | None:
    """Normalize parsed item text."""
    if value is None:
        return None
    item = value.strip(" ,.-").lower()
    return item or None


def _clean_name(value: str | None) -> str | None:
    """Normalize parsed customer names."""
    if value is None:
        return None
    name = value.strip(" ,.-")
    if not name:
        return None
    return " ".join(part.capitalize() for part in name.split())


def _to_float(value: str | None) -> float | None:
    """Convert a numeric string to float without binary rounding surprises."""
    if value is None:
        return None
    try:
        return float(Decimal(value))
    except (InvalidOperation, ValueError):
        return None
