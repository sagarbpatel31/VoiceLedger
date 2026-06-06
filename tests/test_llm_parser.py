from voiceledger.parser.llm_parser import LLMParser
from voiceledger.parser.rules import RuleParser
from voiceledger.parser.schema import Transaction


class FakeInferenceClient:
    def __init__(self, response: object) -> None:
        self.response = response

    def text_generation(self, prompt: str, **kwargs: object) -> object:
        self.prompt = prompt
        self.kwargs = kwargs
        return self.response


def test_rule_parser_implements_parser_interface() -> None:
    transaction = RuleParser().parse("Sold 12 mangoes, 20 each")

    assert isinstance(transaction, Transaction)
    assert transaction.transaction_type == "sale"
    assert transaction.amount == 240


def test_llm_parser_returns_valid_transaction_from_strict_json() -> None:
    client = FakeInferenceClient(
        """
        {
          "transaction_type": "customer_credit",
          "item": null,
          "quantity": null,
          "unit_price": null,
          "amount": 100,
          "customer": "Amit",
          "payment_status": "credit",
          "notes": "Amit owes 100",
          "confidence": 0.97
        }
        """
    )

    transaction = LLMParser(client=client, model="test-model").parse("Amit owes 100")

    assert transaction.transaction_type == "customer_credit"
    assert transaction.customer == "Amit"
    assert transaction.amount == 100
    assert client.kwargs["temperature"] == 0.0
    assert client.kwargs["model"] == "test-model"


def test_llm_parser_falls_back_to_rules_on_invalid_json() -> None:
    client = FakeInferenceClient("not json")

    transaction = LLMParser(client=client).parse("Sold 12 mangoes, 20 each")

    assert transaction.transaction_type == "sale"
    assert transaction.item == "mangoes"
    assert transaction.amount == 240


def test_llm_parser_falls_back_to_rules_on_schema_error() -> None:
    client = FakeInferenceClient(
        """
        {
          "transaction_type": "not_supported",
          "notes": "Amit owes 100",
          "confidence": 0.9
        }
        """
    )

    transaction = LLMParser(client=client).parse("Amit owes 100")

    assert transaction.transaction_type == "customer_credit"
    assert transaction.customer == "Amit"
    assert transaction.amount == 100
