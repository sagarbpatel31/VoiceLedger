"""Gradio application for the VoiceLedger MVP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gradio as gr
import pandas as pd

from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.database import add_transaction, get_transactions, initialize_database
from voiceledger.ledger.inventory import get_inventory
from voiceledger.parser.rules import parse_transaction
from voiceledger.parser.schema import Transaction
from voiceledger.speech.transcribe import TranscriptionError, transcribe_audio


LOW_STOCK_THRESHOLD = 5


def create_app(db_path: str | Path | None = None) -> gr.Blocks:
    """Create and return the Gradio Blocks app."""
    initialize_database(db_path)

    with gr.Blocks(title="VoiceLedger") as demo:
        gr.Markdown("# VoiceLedger")

        parsed_state = gr.State(value=None)

        with gr.Tab("Record Transaction"):
            with gr.Row():
                with gr.Column():
                    note_input = gr.Textbox(
                        label="Transaction note",
                        placeholder="Sold 12 mangoes, 20 each",
                        lines=4,
                    )
                    parse_button = gr.Button("Parse Text", variant="primary")
                with gr.Column():
                    audio_input = gr.Audio(
                        label="Record transaction",
                        sources=["microphone"],
                        type="filepath",
                    )
                    transcribe_button = gr.Button("Transcribe & Parse", variant="primary")
                    transcript_output = gr.Textbox(
                        label="Transcript",
                        lines=3,
                        interactive=False,
                    )

            with gr.Row():
                save_button = gr.Button("Save")

            structured_output = gr.JSON(label="Structured output")
            status_output = gr.Markdown()

            parse_button.click(
                fn=_parse_note,
                inputs=note_input,
                outputs=[structured_output, parsed_state, status_output],
            )
            transcribe_button.click(
                fn=_transcribe_and_parse_audio,
                inputs=audio_input,
                outputs=[transcript_output, structured_output, parsed_state, status_output],
            )
            save_button.click(
                fn=lambda transaction: _save_transaction(transaction, db_path),
                inputs=parsed_state,
                outputs=status_output,
            )

        with gr.Tab("Customer Credit Book"):
            refresh_customer_button = gr.Button("Refresh Customer Credit Book")
            customer_balances_output = gr.Dataframe(
                headers=["customer", "outstanding_balance"],
                label="Customer balances",
                interactive=False,
                wrap=True,
            )
            refresh_customer_button.click(
                fn=lambda: get_customer_balances(db_path),
                inputs=None,
                outputs=customer_balances_output,
            )
            demo.load(
                fn=lambda: get_customer_balances(db_path),
                inputs=None,
                outputs=customer_balances_output,
            )

        with gr.Tab("Inventory"):
            refresh_inventory_button = gr.Button("Refresh Inventory")
            inventory_output = gr.Dataframe(
                headers=["item", "current_stock"],
                label="Current stock",
                interactive=False,
                wrap=True,
            )
            refresh_inventory_button.click(
                fn=lambda: _get_inventory_display(db_path),
                inputs=None,
                outputs=inventory_output,
            )
            demo.load(
                fn=lambda: _get_inventory_display(db_path),
                inputs=None,
                outputs=inventory_output,
            )

        with gr.Tab("Ledger"):
            refresh_button = gr.Button("Refresh Ledger")
            ledger_output = gr.Dataframe(
                headers=[
                    "id",
                    "transaction_type",
                    "item",
                    "quantity",
                    "unit_price",
                    "amount",
                    "customer",
                    "payment_status",
                    "notes",
                    "confidence",
                    "created_at",
                ],
                label="Saved transactions",
                interactive=False,
                wrap=True,
            )
            refresh_button.click(
                fn=lambda: get_transactions(db_path),
                inputs=None,
                outputs=ledger_output,
            )
            demo.load(
                fn=lambda: get_transactions(db_path),
                inputs=None,
                outputs=ledger_output,
            )

    return demo


def _parse_note(note: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Parse a note and return display data plus serializable state."""
    transaction = parse_transaction(note)
    payload = transaction.model_dump()
    status = _status_message(transaction)
    return payload, payload, status


def _transcribe_and_parse_audio(audio_path: str | None) -> tuple[str, dict[str, Any], dict[str, Any] | None, str]:
    """Transcribe recorded audio, parse the transcript, and return UI updates."""
    try:
        transcript = transcribe_audio(audio_path)
    except TranscriptionError as exc:
        empty_payload = _empty_transaction_payload()
        return "", empty_payload, None, f"Transcription failed: {exc}"

    transaction = parse_transaction(transcript)
    payload = transaction.model_dump()
    return transcript, payload, payload, _status_message(transaction)


def _save_transaction(transaction_payload: dict[str, Any] | None, db_path: str | Path | None) -> str:
    """Save the parsed transaction payload to SQLite."""
    if not transaction_payload:
        return "Parse a transaction before saving."

    transaction = Transaction(**transaction_payload)
    transaction_id = add_transaction(transaction, db_path)
    return f"Saved transaction #{transaction_id}."


def _get_inventory_display(db_path: str | Path | None) -> pd.io.formats.style.Styler:
    """Return inventory with low-stock rows highlighted for Gradio display."""
    inventory = get_inventory(db_path)
    return inventory.style.apply(_highlight_low_stock, axis=1)


def _highlight_low_stock(row: pd.Series) -> list[str]:
    """Highlight rows where stock is below the configured threshold."""
    current_stock = row.get("current_stock")
    if current_stock is not None and float(current_stock) < LOW_STOCK_THRESHOLD:
        return ["background-color: #fff3cd; color: #5f370e"] * len(row)
    return [""] * len(row)


def _empty_transaction_payload() -> dict[str, Any]:
    """Return a serializable empty transaction for UI display."""
    return Transaction().model_dump()


def _status_message(transaction: Transaction) -> str:
    """Return a human-readable parsing status."""
    if transaction.transaction_type == "unknown":
        return "Could not confidently parse this note. You can still inspect the structured output."
    return f"Parsed as `{transaction.transaction_type}` with confidence `{transaction.confidence:.2f}`."
