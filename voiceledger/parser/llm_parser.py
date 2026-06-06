"""LLM parser abstraction with strict Transaction schema fallback."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

from voiceledger.parser.base import Parser
from voiceledger.parser.rules import RuleParser
from voiceledger.parser.schema import Transaction


SYSTEM_PROMPT = """You extract bookkeeping transactions for VoiceLedger.
Return only strict JSON matching this schema:
{
  "transaction_type": "sale|expense|inventory_purchase|customer_credit|customer_payment|unknown",
  "item": "string or null",
  "quantity": "number or null",
  "unit_price": "number or null",
  "amount": "number or null",
  "customer": "string or null",
  "payment_status": "paid|unpaid|credit|unknown",
  "notes": "original user text",
  "confidence": "number from 0 to 1"
}
Do not include markdown, prose, comments, or extra keys."""


class HuggingFaceInferenceClient(Protocol):
    """Minimal Hugging Face Inference API compatible client interface."""

    def text_generation(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt."""


class LLMParser(Parser):
    """Parse transaction text with an LLM and fall back to rule parsing on failure."""

    def __init__(
        self,
        client: HuggingFaceInferenceClient | Callable[..., Any],
        model: str | None = None,
        fallback_parser: Parser | None = None,
    ) -> None:
        """Create an LLM-backed parser.

        The client can be a Hugging Face Inference API style object with a
        `text_generation()` method or a callable that accepts `prompt` and
        generation keyword arguments.
        """
        self.client = client
        self.model = model
        self.fallback_parser = fallback_parser or RuleParser()

    def parse(self, text: str) -> Transaction:
        """Parse text with strict JSON generation and schema validation."""
        try:
            response = self._generate(text)
            payload = _extract_json_object(response)
            transaction = Transaction.model_validate(payload)
            return transaction.model_copy(update={"notes": transaction.notes or text.strip()})
        except Exception:
            return self.fallback_parser.parse(text)

    def _generate(self, text: str) -> str:
        """Call the configured Hugging Face compatible generation client."""
        prompt = _build_prompt(text)
        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": 256,
            "temperature": 0.0,
            "return_full_text": False,
        }
        if self.model is not None:
            generation_kwargs["model"] = self.model

        if hasattr(self.client, "text_generation"):
            response = self.client.text_generation(prompt, **generation_kwargs)
        else:
            response = self.client(prompt=prompt, **generation_kwargs)

        return _coerce_generation_text(response)


def _build_prompt(text: str) -> str:
    """Build a strict JSON extraction prompt."""
    return f"{SYSTEM_PROMPT}\n\nUser text: {text.strip()}\nJSON:"


def _extract_json_object(response: str) -> dict[str, Any]:
    """Extract and parse the first JSON object from generated text."""
    start = response.find("{")
    end = response.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM response did not contain a JSON object.")

    payload = json.loads(response[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("LLM response JSON must be an object.")
    return payload


def _coerce_generation_text(response: Any) -> str:
    """Normalize common Hugging Face generation response shapes to text."""
    if isinstance(response, str):
        return response

    if isinstance(response, list) and response:
        first = response[0]
        if isinstance(first, dict):
            return str(first.get("generated_text", ""))

    if isinstance(response, dict):
        return str(response.get("generated_text", response.get("text", "")))

    raise ValueError("Unsupported generation response shape.")
