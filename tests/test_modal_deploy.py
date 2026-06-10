import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from backend import modal_deploy


def _client() -> TestClient:
    return TestClient(modal_deploy.api.get_raw_f()())


def test_modal_parse_route_accepts_json_body(monkeypatch) -> None:
    response_payload = {
        "transaction_type": "sale",
        "item": "mangoes",
        "quantity": 12,
        "unit_price": 20,
        "amount": 240,
        "customer": None,
        "payment_status": "paid",
        "notes": "Sold 12 mangoes, 20 each",
        "confidence": 0.94,
    }
    monkeypatch.setattr(modal_deploy, "_generate_nemotron_json", lambda text, prompt: json.dumps(response_payload))

    response = _client().post("/parse", json={"text": "Sold 12 mangoes, 20 each"})

    assert response.status_code == 200
    transaction = response.json()["transaction"]
    assert transaction["transaction_type"] == "sale"
    assert transaction["amount"] == 240


def test_modal_parse_route_accepts_raw_text_body(monkeypatch) -> None:
    def fail_model(text: str, prompt: str) -> str:
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(modal_deploy, "_generate_nemotron_json", fail_model)

    response = _client().post("/parse", content="Paid 500 for supplies")

    assert response.status_code == 200
    transaction = response.json()["transaction"]
    assert transaction["transaction_type"] == "expense"
    assert transaction["amount"] == 500


def test_modal_parse_route_handles_empty_body() -> None:
    response = _client().post("/parse", content="")

    assert response.status_code == 200
    transaction = response.json()["transaction"]
    assert transaction["transaction_type"] == "unknown"
    assert transaction["confidence"] == 0


def test_modal_parse_route_falls_back_when_model_output_is_invalid(monkeypatch) -> None:
    monkeypatch.setattr(modal_deploy, "_generate_nemotron_json", lambda text, prompt: "not json")

    response = _client().post("/parse", json={"text": "Amit owes 100"})

    assert response.status_code == 200
    transaction = response.json()["transaction"]
    assert transaction["transaction_type"] == "customer_credit"
    assert transaction["customer"] == "Amit"
