"""Modal API client with local fallbacks for Hugging Face Spaces."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests

from voiceledger.parser.schema import Transaction


MODAL_TRANSCRIBE_URL_ENV = "VOICELEDGER_MODAL_TRANSCRIBE_URL"
MODAL_PARSE_URL_ENV = "VOICELEDGER_MODAL_PARSE_URL"
MODAL_TOKEN_ENV = "VOICELEDGER_MODAL_API_TOKEN"
REQUEST_TIMEOUT_SECONDS = 120


def transcribe_audio(
    audio_path: Any,
    fallback: Callable[[Any], str],
) -> str:
    """Transcribe audio through Modal, falling back locally if unavailable."""
    path = _coerce_audio_path(audio_path)
    endpoint_url = os.getenv(MODAL_TRANSCRIBE_URL_ENV)
    if not endpoint_url or path is None:
        return fallback(audio_path)

    if not path.exists():
        return fallback(audio_path)

    try:
        with path.open("rb") as audio_file:
            response = requests.post(
                endpoint_url,
                headers=_auth_headers(),
                files={"audio": (path.name, audio_file, "application/octet-stream")},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        response.raise_for_status()
        payload = response.json()
        transcript = str(payload.get("transcript", "")).strip()
        if not transcript:
            raise ValueError("Modal transcription response did not include a transcript.")
        return transcript
    except Exception:
        return fallback(audio_path)


def parse_transaction(
    text: str,
    fallback: Callable[[str], Transaction],
) -> Transaction:
    """Parse transaction text through Modal, falling back locally if unavailable."""
    endpoint_url = os.getenv(MODAL_PARSE_URL_ENV)
    if not endpoint_url:
        return fallback(text)

    try:
        response = requests.post(
            endpoint_url,
            headers={"Content-Type": "application/json", **_auth_headers()},
            json={"text": text},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        transaction_payload = payload.get("transaction", payload)
        return Transaction.model_validate(transaction_payload)
    except Exception:
        return fallback(text)


def _auth_headers() -> dict[str, str]:
    """Return optional bearer auth headers for Modal endpoints."""
    token = os.getenv(MODAL_TOKEN_ENV)
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _coerce_audio_path(audio_value: Any) -> Path | None:
    """Extract a local audio filepath from Gradio audio values."""
    if audio_value is None:
        return None
    if isinstance(audio_value, (str, Path)):
        return Path(audio_value)
    if isinstance(audio_value, dict):
        for key in ("path", "name", "file", "filepath"):
            value = audio_value.get(key)
            if value:
                return Path(value)
    if isinstance(audio_value, (list, tuple)):
        for value in audio_value:
            path = _coerce_audio_path(value)
            if path is not None:
                return path
    return None
