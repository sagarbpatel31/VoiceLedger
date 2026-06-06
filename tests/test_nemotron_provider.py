import json

import pytest

from voiceledger.parser.providers.nemotron import NemotronParser


class FakeGenerator:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls = []

    def __call__(self, prompt: str, **kwargs: object) -> object:
        self.calls.append((prompt, kwargs))
        return self.response


@pytest.mark.parametrize(
    ("response", "transaction_type", "amount"),
    [
        (
            {
                "transaction_type": "sale",
                "item": "mangoes",
                "quantity": 12,
                "unit_price": 20,
                "amount": 240,
                "customer": None,
                "payment_status": "paid",
                "notes": "Sold 12 mangoes, 20 each",
                "confidence": 0.94,
            },
            "sale",
            240,
        ),
        (
            {
                "transaction_type": "expense",
                "item": "rent",
                "quantity": None,
                "unit_price": None,
                "amount": 300,
                "customer": None,
                "payment_status": "paid",
                "notes": "rent 300",
                "confidence": 0.88,
            },
            "expense",
            300,
        ),
        (
            {
                "transaction_type": "inventory_purchase",
                "item": "onions",
                "quantity": 20,
                "unit_price": None,
                "amount": None,
                "customer": None,
                "payment_status": "paid",
                "notes": "Bought 20 onions",
                "confidence": 0.86,
            },
            "inventory_purchase",
            None,
        ),
        (
            {
                "transaction_type": "customer_credit",
                "item": None,
                "quantity": None,
                "unit_price": None,
                "amount": 100,
                "customer": "Amit",
                "payment_status": "credit",
                "notes": "Amit owes 100",
                "confidence": 0.9,
            },
            "customer_credit",
            100,
        ),
    ],
)
def test_nemotron_parser_supports_core_transaction_types(response, transaction_type, amount) -> None:
    generator = FakeGenerator([{"generated_text": json.dumps(response)}])

    transaction = NemotronParser(generator=generator).parse(response["notes"])

    assert transaction.transaction_type == transaction_type
    assert transaction.amount == amount
    assert transaction.confidence > 0
    assert generator.calls[0][1]["do_sample"] is False
    assert generator.calls[0][1]["temperature"] == 0.0


def test_nemotron_parser_adds_confidence_when_model_omits_meaningful_score() -> None:
    generator = FakeGenerator(
        [
            {
                "generated_text": """
                {
                  "transaction_type": "expense",
                  "item": "rent",
                  "quantity": null,
                  "unit_price": null,
                  "amount": 300,
                  "customer": null,
                  "payment_status": "paid",
                  "notes": "rent 300",
                  "confidence": 0
                }
                """
            }
        ]
    )

    transaction = NemotronParser(generator=generator).parse("rent 300")

    assert transaction.transaction_type == "expense"
    assert transaction.confidence >= 0.8


def test_nemotron_parser_falls_back_to_rules_on_invalid_output() -> None:
    generator = FakeGenerator("not json")

    transaction = NemotronParser(generator=generator).parse("mango 12 x 20")

    assert transaction.transaction_type == "sale"
    assert transaction.amount == 240
