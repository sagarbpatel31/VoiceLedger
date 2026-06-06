"""NVIDIA Nemotron parser provider using transformers."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from voiceledger.parser.base import Parser
from voiceledger.parser.rules import RuleParser
from voiceledger.parser.schema import Transaction


DEFAULT_NEMOTRON_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-4B"
NEMOTRON_MODEL_ENV = "VOICELEDGER_NEMOTRON_MODEL"

NEMOTRON_SYSTEM_PROMPT = """You are VoiceLedger's bookkeeping parser.
Return only one strict JSON object with these exact keys:
{
  "transaction_type": "sale|expense|inventory_purchase|customer_credit|customer_payment|unknown",
  "item": "string or null",
  "quantity": "number or null",
  "unit_price": "number or null",
  "amount": "number or null",
  "customer": "string or null",
  "payment_status": "paid|unpaid|credit|unknown",
  "notes": "original input text",
  "confidence": "number from 0.0 to 1.0"
}
Supported intents: sales, expenses, inventory purchases, customer credit, and customer payments.
Do not include markdown, comments, explanations, or extra keys."""


class NemotronParser(Parser):
    """Parser provider backed by NVIDIA Nemotron through transformers."""

    def __init__(
        self,
        model_id: str | None = None,
        generator: Callable[..., Any] | None = None,
        fallback_parser: Parser | None = None,
    ) -> None:
        """Create a Nemotron parser.

        `generator` is injectable for tests. In production it defaults to a
        lazily loaded `transformers.pipeline("text-generation")`.
        """
        self.model_id = model_id or os.getenv(NEMOTRON_MODEL_ENV, DEFAULT_NEMOTRON_MODEL)
        self.generator = generator
        self.fallback_parser = fallback_parser or RuleParser()

    def parse(self, text: str) -> Transaction:
        """Parse text into a Transaction, falling back to rules on failure."""
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return Transaction(notes="", confidence=0.0)

        try:
            generated_text = self._generate(cleaned_text)
            payload = _extract_json_object(generated_text)
            transaction = Transaction.model_validate(payload)
            return _normalize_transaction(transaction, cleaned_text)
        except Exception:
            return self.fallback_parser.parse(cleaned_text)

    def _generate(self, text: str) -> str:
        """Generate parser JSON with Nemotron."""
        generator = self.generator or _get_text_generation_pipeline(self.model_id)
        prompt = _build_prompt(text)
        response = generator(
            prompt,
            max_new_tokens=256,
            do_sample=False,
            temperature=0.0,
            return_full_text=False,
        )
        return _coerce_generation_text(response)


def _build_prompt(text: str) -> str:
    """Build the strict JSON prompt for Nemotron."""
    return f"{NEMOTRON_SYSTEM_PROMPT}\n\nInput: {text}\nJSON:"


@lru_cache(maxsize=2)
def _get_text_generation_pipeline(model_id: str) -> Callable[..., Any]:
    """Load and cache a transformers text-generation pipeline."""
    try:
        from transformers import pipeline
    except ImportError as exc:  # pragma: no cover - environment dependent.
        raise RuntimeError("transformers is not installed. Install dependencies from requirements.txt.") from exc

    return pipeline(
        "text-generation",
        model=model_id,
        tokenizer=model_id,
        device_map="auto",
        torch_dtype="auto",
    )


def _extract_json_object(response: str) -> dict[str, Any]:
    """Extract a JSON object from generated text."""
    start = response.find("{")
    end = response.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Nemotron response did not contain JSON.")

    payload = json.loads(response[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Nemotron response JSON must be an object.")
    return payload


def _coerce_generation_text(response: Any) -> str:
    """Normalize common transformers generation outputs into text."""
    if isinstance(response, str):
        return response

    if isinstance(response, list) and response:
        first = response[0]
        if isinstance(first, dict):
            return str(first.get("generated_text", ""))
        return str(first)

    if isinstance(response, dict):
        return str(response.get("generated_text", response.get("text", "")))

    raise ValueError("Unsupported Nemotron generation response shape.")


def _normalize_transaction(transaction: Transaction, source_text: str) -> Transaction:
    """Ensure notes and confidence are always populated."""
    updates: dict[str, Any] = {}
    if not transaction.notes:
        updates["notes"] = source_text
    if transaction.confidence <= 0:
        updates["confidence"] = _confidence_for_transaction(transaction)
    if not updates:
        return transaction
    return transaction.model_copy(update=updates)


def _confidence_for_transaction(transaction: Transaction) -> float:
    """Assign a conservative confidence score when the model omits one."""
    score = 0.45
    if transaction.transaction_type != "unknown":
        score += 0.2
    if transaction.amount is not None or transaction.quantity is not None:
        score += 0.15
    if transaction.item or transaction.customer:
        score += 0.1
    return min(round(score, 2), 0.9)
