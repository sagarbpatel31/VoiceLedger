"""Modal API client with local fallbacks for Hugging Face Spaces."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from voiceledger.parser.schema import Transaction


MODAL_TRANSCRIBE_URL_ENV = "VOICELEDGER_MODAL_TRANSCRIBE_URL"
MODAL_PARSE_URL_ENV = "VOICELEDGER_MODAL_PARSE_URL"
MODAL_TOKEN_ENV = "VOICELEDGER_MODAL_API_TOKEN"
REQUEST_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class ParseResult:
    """Parsed transaction with source and fallback details."""

    transaction: Transaction
    source: str
    message: str
    fallback_reason: str | None = None


@dataclass(frozen=True)
class TranscriptionResult:
    """Audio transcript with source and fallback details."""

    transcript: str
    source: str
    message: str
    fallback_reason: str | None = None


def transcribe_audio(
    audio_path: Any,
    fallback: Callable[[Any], str],
    force_local: bool = False,
) -> str:
    """Transcribe audio through Modal, falling back locally if unavailable."""
    return transcribe_audio_result(audio_path, fallback=fallback, force_local=force_local).transcript


def transcribe_audio_result(
    audio_path: Any,
    fallback: Callable[[Any], str],
    force_local: bool = False,
) -> TranscriptionResult:
    """Transcribe audio and return source metadata for UI observability."""
    if force_local:
        transcript = fallback(audio_path)
        return TranscriptionResult(
            transcript=transcript,
            source="local",
            message="Transcribed locally with faster-whisper.",
            fallback_reason="Cloud AI is disabled for local-first mode.",
        )

    path = _coerce_audio_path(audio_path)
    endpoint_url = os.getenv(MODAL_TRANSCRIBE_URL_ENV)
    if not endpoint_url or path is None:
        transcript = fallback(audio_path)
        return TranscriptionResult(
            transcript=transcript,
            source="local",
            message="Transcribed locally with faster-whisper.",
            fallback_reason="Modal transcription endpoint is not configured." if not endpoint_url else "Audio path was unavailable.",
        )

    if not path.exists():
        transcript = fallback(audio_path)
        return TranscriptionResult(
            transcript=transcript,
            source="local",
            message="Transcribed locally with faster-whisper.",
            fallback_reason="Recorded audio file was not found for Modal upload.",
        )

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
        return TranscriptionResult(
            transcript=transcript,
            source="modal",
            message="Transcribed by Modal faster-whisper endpoint.",
        )
    except Exception as exc:
        transcript = fallback(audio_path)
        return TranscriptionResult(
            transcript=transcript,
            source="local",
            message="Transcribed locally with faster-whisper after Modal failed.",
            fallback_reason=_format_exception(exc),
        )


def parse_transaction(
    text: str,
    fallback: Callable[[str], Transaction],
    force_local: bool = False,
) -> Transaction:
    """Parse transaction text through Modal, falling back locally if unavailable."""
    return parse_transaction_result(text, fallback=fallback, force_local=force_local).transaction


def parse_transaction_result(
    text: str,
    fallback: Callable[[str], Transaction],
    force_local: bool = False,
) -> ParseResult:
    """Parse text and return source metadata for UI observability."""
    if force_local:
        return ParseResult(
            transaction=fallback(text),
            source="local",
            message="Parsed locally with the rule parser.",
            fallback_reason="Cloud AI is disabled for local-first mode.",
        )

    endpoint_url = os.getenv(MODAL_PARSE_URL_ENV)
    if not endpoint_url:
        return ParseResult(
            transaction=fallback(text),
            source="local",
            message="Parsed locally with the rule parser.",
            fallback_reason="Modal parser endpoint is not configured.",
        )

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
        return ParseResult(
            transaction=Transaction.model_validate(transaction_payload),
            source="modal",
            message="Parsed by Modal using NVIDIA Nemotron.",
        )
    except Exception as exc:
        return ParseResult(
            transaction=fallback(text),
            source="local",
            message="Parsed locally with the rule parser after Modal failed.",
            fallback_reason=_format_exception(exc),
        )


def get_modal_health() -> dict[str, str]:
    """Return a lightweight Modal health snapshot for the UI."""
    parse_url = os.getenv(MODAL_PARSE_URL_ENV)
    transcribe_url = os.getenv(MODAL_TRANSCRIBE_URL_ENV)
    health_url = _sibling_endpoint(parse_url or transcribe_url, "health")
    version_url = _sibling_endpoint(parse_url or transcribe_url, "version")

    if not health_url:
        return {
            "status": "not_configured",
            "version": "not_configured",
            "message": "Modal endpoints are not configured.",
        }

    try:
        health_response = requests.get(health_url, headers=_auth_headers(), timeout=10)
        health_response.raise_for_status()
        health_payload = health_response.json()
        status = str(health_payload.get("status", "ok"))
    except Exception as exc:
        return {
            "status": "unavailable",
            "version": "unknown",
            "message": f"Modal health check failed: {_format_exception(exc)}",
        }

    version = "unknown"
    if version_url:
        try:
            version_response = requests.get(version_url, headers=_auth_headers(), timeout=10)
            version_response.raise_for_status()
            version_payload = version_response.json()
            version = str(version_payload.get("version", "unknown"))
        except Exception as exc:
            version = f"unknown ({_format_exception(exc)})"

    return {
        "status": status,
        "version": version,
        "message": "Modal backend is reachable.",
    }


def _auth_headers() -> dict[str, str]:
    """Return optional bearer auth headers for Modal endpoints."""
    token = os.getenv(MODAL_TOKEN_ENV)
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _sibling_endpoint(endpoint_url: str | None, route: str) -> str | None:
    """Build a sibling API endpoint URL from a configured Modal route."""
    if not endpoint_url:
        return None
    base_url = endpoint_url.rstrip("/")
    for suffix in ("/parse", "/transcribe", "/health", "/version"):
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
            break
    return f"{base_url}/{route.lstrip('/')}"


def _format_exception(exc: Exception) -> str:
    """Return a concise exception summary for user-facing fallback messages."""
    detail = str(exc).strip()
    if not detail:
        return exc.__class__.__name__
    return f"{exc.__class__.__name__}: {detail}"


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
