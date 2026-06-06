from pathlib import Path

from backend import modal_api
from voiceledger.parser.rules import parse_transaction as local_parse_transaction


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_parse_transaction_uses_local_fallback_when_url_missing(monkeypatch) -> None:
    monkeypatch.delenv(modal_api.MODAL_PARSE_URL_ENV, raising=False)

    transaction = modal_api.parse_transaction("Amit owes 100", fallback=local_parse_transaction)

    assert transaction.transaction_type == "customer_credit"
    assert transaction.customer == "Amit"


def test_parse_transaction_uses_modal_response(monkeypatch) -> None:
    monkeypatch.setenv(modal_api.MODAL_PARSE_URL_ENV, "https://modal.example/parse")

    def fake_post(*args, **kwargs) -> FakeResponse:
        return FakeResponse(
            {
                "transaction": {
                    "transaction_type": "expense",
                    "item": "rent",
                    "quantity": None,
                    "unit_price": None,
                    "amount": 300,
                    "customer": None,
                    "payment_status": "paid",
                    "notes": "rent 300",
                    "confidence": 0.99,
                }
            }
        )

    monkeypatch.setattr(modal_api.requests, "post", fake_post)

    transaction = modal_api.parse_transaction("rent 300", fallback=local_parse_transaction)

    assert transaction.transaction_type == "expense"
    assert transaction.item == "rent"
    assert transaction.amount == 300


def test_parse_transaction_falls_back_when_modal_errors(monkeypatch) -> None:
    monkeypatch.setenv(modal_api.MODAL_PARSE_URL_ENV, "https://modal.example/parse")

    def fake_post(*args, **kwargs) -> None:
        raise RuntimeError("network down")

    monkeypatch.setattr(modal_api.requests, "post", fake_post)

    transaction = modal_api.parse_transaction("mango 12 x 20", fallback=local_parse_transaction)

    assert transaction.transaction_type == "sale"
    assert transaction.amount == 240


def test_transcribe_audio_uses_modal_response(tmp_path: Path, monkeypatch) -> None:
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"audio")
    monkeypatch.setenv(modal_api.MODAL_TRANSCRIBE_URL_ENV, "https://modal.example/transcribe")

    def fake_post(*args, **kwargs) -> FakeResponse:
        return FakeResponse({"transcript": "Sold 12 mangoes"})

    monkeypatch.setattr(modal_api.requests, "post", fake_post)

    transcript = modal_api.transcribe_audio(audio_path, fallback=lambda _: "fallback")

    assert transcript == "Sold 12 mangoes"


def test_transcribe_audio_falls_back_when_url_missing(tmp_path: Path, monkeypatch) -> None:
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"audio")
    monkeypatch.delenv(modal_api.MODAL_TRANSCRIBE_URL_ENV, raising=False)

    transcript = modal_api.transcribe_audio(audio_path, fallback=lambda _: "fallback transcript")

    assert transcript == "fallback transcript"
