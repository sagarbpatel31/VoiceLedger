"""Gradio application for the VoiceLedger MVP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gradio as gr
import pandas as pd

from backend import modal_api
from voiceledger.ledger.analytics import (
    calculate_daily_expenses,
    calculate_daily_sales,
    calculate_net_profit,
    low_stock_items,
    outstanding_credit,
    top_selling_items,
)
from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.database import add_transaction, get_transactions, initialize_database
from voiceledger.ledger.inventory import get_inventory
from voiceledger.parser.bulk import REVIEW_COLUMNS, parse_bulk_notes, review_table_to_transactions
from voiceledger.parser.rules import parse_transaction as local_parse_transaction
from voiceledger.parser.schema import Transaction
from voiceledger.reports.pdf_report import generate_daily_summary_pdf
from voiceledger.reports.whatsapp_summary import generate_whatsapp_summary
from voiceledger.speech.transcribe import TranscriptionError, transcribe_audio as local_transcribe_audio
from voiceledger.ui.theme import APP_CSS, create_theme


LOW_STOCK_THRESHOLD = 5


def create_app(db_path: str | Path | None = None) -> gr.Blocks:
    """Create and return the Gradio Blocks app."""
    initialize_database(db_path)

    with gr.Blocks(
        title="VoiceLedger",
        theme=create_theme(),
        css=APP_CSS,
        elem_id="voiceledger-app",
    ) as demo:
        gr.HTML(
            """
            <section class="vl-hero">
              <h1>VoiceLedger</h1>
              <p>Daily sales, credit, stock, and reports in one working screen.</p>
            </section>
            """
        )

        parsed_state = gr.State(value=None)

        with gr.Tab("Dashboard"):
            refresh_dashboard_button = gr.Button("Refresh Dashboard", variant="primary")
            with gr.Row(elem_classes="vl-metric-grid"):
                total_sales_output = gr.HTML()
                total_expenses_output = gr.HTML()
                net_profit_output = gr.HTML()
                outstanding_credit_output = gr.HTML()
            top_selling_item_output = gr.Textbox(label="Top Selling Item", interactive=False)
            with gr.Row():
                top_items_plot = gr.BarPlot(
                    x="item",
                    y="quantity_sold",
                    title="Top Selling Items",
                    x_title="Item",
                    y_title="Quantity Sold",
                    vertical=False,
                    elem_classes="vl-panel",
                )
                low_stock_output = gr.Dataframe(
                    headers=["item", "current_stock"],
                    label="Low Inventory Alerts",
                    interactive=False,
                    wrap=True,
                    elem_classes="vl-panel",
                )
            refresh_dashboard_button.click(
                fn=lambda: _get_dashboard_data(db_path),
                inputs=None,
                outputs=[
                    total_sales_output,
                    total_expenses_output,
                    net_profit_output,
                    outstanding_credit_output,
                    top_selling_item_output,
                    top_items_plot,
                    low_stock_output,
                ],
            )
            demo.load(
                fn=lambda: _get_dashboard_data(db_path),
                inputs=None,
                outputs=[
                    total_sales_output,
                    total_expenses_output,
                    net_profit_output,
                    outstanding_credit_output,
                    top_selling_item_output,
                    top_items_plot,
                    low_stock_output,
                ],
            )

        with gr.Tab("Record"):
            with gr.Row():
                with gr.Column():
                    note_input = gr.Textbox(
                        label="Transaction note",
                        placeholder="Sold 12 mangoes, 20 each",
                        lines=4,
                        elem_classes="vl-panel",
                    )
                    parse_button = gr.Button("Parse Text", variant="primary")
                with gr.Column():
                    audio_input = gr.Audio(
                        label="Record transaction",
                        sources=["microphone"],
                        type="filepath",
                        elem_classes="vl-panel",
                    )
                    transcribe_button = gr.Button("Transcribe & Parse", variant="primary")
                    transcript_output = gr.Textbox(
                        label="Transcript",
                        lines=3,
                        interactive=False,
                        elem_classes="vl-panel",
                    )

            with gr.Row():
                save_button = gr.Button("Save")

            structured_output = gr.JSON(label="Structured output", elem_classes="vl-panel")
            status_output = gr.Markdown(elem_classes="vl-status")

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

        with gr.Tab("Bulk Import"):
            bulk_notes_input = gr.Textbox(
                label="Paste transaction notes",
                placeholder="mango 12 x 20\nrent 300\nAmit owes 100\nRamesh paid 50",
                lines=8,
                elem_classes="vl-panel",
            )
            with gr.Row():
                bulk_parse_button = gr.Button("Parse Lines", variant="primary")
                bulk_save_button = gr.Button("Save All Transactions")
            bulk_review_output = gr.Dataframe(
                headers=REVIEW_COLUMNS,
                label="Review and edit transactions",
                interactive=True,
                wrap=True,
                elem_classes="vl-panel",
            )
            bulk_status_output = gr.Markdown(elem_classes="vl-status")
            bulk_parse_button.click(
                fn=_parse_bulk_notes_for_review,
                inputs=bulk_notes_input,
                outputs=[bulk_review_output, bulk_status_output],
            )
            bulk_save_button.click(
                fn=lambda review_table: _save_bulk_transactions(review_table, db_path),
                inputs=bulk_review_output,
                outputs=bulk_status_output,
            )

        with gr.Tab("Customer Credit Book"):
            refresh_customer_button = gr.Button("Refresh Customer Credit Book")
            customer_balances_output = gr.Dataframe(
                headers=["customer", "outstanding_balance"],
                label="Customer balances",
                interactive=False,
                wrap=True,
                elem_classes="vl-panel",
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
                elem_classes="vl-panel",
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

        with gr.Tab("Reports"):
            generate_report_button = gr.Button("Generate Daily Summary PDF", variant="primary")
            report_status_output = gr.Markdown(elem_classes="vl-status")
            report_file_output = gr.File(label="Daily Summary PDF", elem_classes="vl-panel")
            generate_report_button.click(
                fn=lambda: _generate_daily_summary_report(db_path),
                inputs=None,
                outputs=[report_file_output, report_status_output],
            )
            gr.Markdown("### WhatsApp Summary")
            generate_whatsapp_button = gr.Button("Generate WhatsApp Summary")
            whatsapp_summary_output = gr.Textbox(
                label="WhatsApp Summary",
                lines=10,
                interactive=False,
                show_copy_button=True,
                elem_classes="vl-panel",
            )
            generate_whatsapp_button.click(
                fn=lambda: generate_whatsapp_summary(
                    db_path=db_path,
                    low_stock_threshold=LOW_STOCK_THRESHOLD,
                ),
                inputs=None,
                outputs=whatsapp_summary_output,
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
                elem_classes="vl-panel",
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
    transaction = modal_api.parse_transaction(note, fallback=local_parse_transaction)
    payload = transaction.model_dump()
    status = _status_message(transaction)
    return payload, payload, status


def _transcribe_and_parse_audio(audio_path: str | None) -> tuple[str, dict[str, Any], dict[str, Any] | None, str]:
    """Transcribe recorded audio, parse the transcript, and return UI updates."""
    try:
        transcript = modal_api.transcribe_audio(audio_path, fallback=local_transcribe_audio)
    except TranscriptionError as exc:
        empty_payload = _empty_transaction_payload()
        return "", empty_payload, None, f"Transcription failed: {exc}"

    transaction = modal_api.parse_transaction(transcript, fallback=local_parse_transaction)
    payload = transaction.model_dump()
    return transcript, payload, payload, _status_message(transaction)


def _save_transaction(transaction_payload: dict[str, Any] | None, db_path: str | Path | None) -> str:
    """Save the parsed transaction payload to SQLite."""
    if not transaction_payload:
        return "Parse a transaction before saving."

    transaction = Transaction(**transaction_payload)
    transaction_id = add_transaction(transaction, db_path)
    return f"Saved transaction #{transaction_id}."


def _parse_bulk_notes_for_review(notes: str) -> tuple[pd.DataFrame, str]:
    """Parse pasted multiline notes into an editable review table."""
    review_table = parse_bulk_notes(
        notes,
        parser=lambda line: modal_api.parse_transaction(line, fallback=local_parse_transaction),
    )
    if review_table.empty:
        return review_table, "Paste one transaction per line, then parse."
    return review_table, f"Parsed {len(review_table)} transaction lines. Review and edit before saving."


def _save_bulk_transactions(review_table: Any, db_path: str | Path | None) -> str:
    """Save all reviewed bulk import transactions."""
    try:
        transactions = review_table_to_transactions(review_table)
    except Exception as exc:
        return f"Could not save bulk import: {exc}"

    if not transactions:
        return "No reviewed transactions to save."

    saved_ids = [add_transaction(transaction, db_path) for transaction in transactions]
    return f"Saved {len(saved_ids)} transactions. Last transaction id: #{saved_ids[-1]}."


def _get_dashboard_data(
    db_path: str | Path | None,
) -> tuple[str, str, str, str, str, pd.DataFrame, pd.DataFrame]:
    """Return business insight values for the Dashboard tab."""
    sales = calculate_daily_sales(db_path)
    expenses = calculate_daily_expenses(db_path)
    profit = calculate_net_profit(db_path)
    credit = outstanding_credit(db_path)
    top_items = top_selling_items(db_path)
    low_stock = low_stock_items(db_path, threshold=LOW_STOCK_THRESHOLD)
    top_item = "No sales recorded today"
    if not top_items.empty:
        first_item = top_items.iloc[0]
        top_item = f"{first_item['item']} ({_format_quantity(first_item['quantity_sold'])} sold)"

    return (
        _metric_card("Total Sales Today", _format_money(sales), "Recorded sales"),
        _metric_card("Total Expenses Today", _format_money(expenses), "Purchases and costs"),
        _metric_card("Net Profit", _format_money(profit), "Sales minus expenses", profit=profit),
        _metric_card("Outstanding Credit", _format_money(credit), "Customer dues"),
        top_item,
        top_items,
        low_stock,
    )


def _get_inventory_display(db_path: str | Path | None) -> pd.io.formats.style.Styler:
    """Return inventory with low-stock rows highlighted for Gradio display."""
    inventory = get_inventory(db_path)
    return inventory.style.apply(_highlight_low_stock, axis=1)


def _generate_daily_summary_report(db_path: str | Path | None) -> tuple[str | None, str]:
    """Generate the Daily Summary PDF for download in Gradio."""
    try:
        report_path = generate_daily_summary_pdf(db_path=db_path)
    except Exception as exc:
        return None, f"Could not generate report: {exc}"
    return str(report_path), "Daily Summary PDF is ready."


def _metric_card(label: str, value: str, note: str, profit: float | None = None) -> str:
    """Render a dashboard metric card."""
    tone = ""
    if profit is not None:
        tone = " vl-profit-positive" if profit >= 0 else " vl-profit-negative"
    return f"""
    <div class="vl-metric-card{tone}">
      <div class="vl-metric-label">{label}</div>
      <div class="vl-metric-value">{value}</div>
      <div class="vl-metric-note">{note}</div>
    </div>
    """


def _format_money(value: float) -> str:
    """Format money for dashboard cards."""
    amount = float(value)
    if amount.is_integer():
        return f"₹{int(amount):,}"
    return f"₹{amount:,.2f}"


def _highlight_low_stock(row: pd.Series) -> list[str]:
    """Highlight rows where stock is below the configured threshold."""
    current_stock = row.get("current_stock")
    if current_stock is not None and float(current_stock) < LOW_STOCK_THRESHOLD:
        return ["background-color: #fff3cd; color: #5f370e"] * len(row)
    return [""] * len(row)


def _format_quantity(value: object) -> str:
    """Format quantity values for concise dashboard text."""
    quantity = float(value)
    if quantity.is_integer():
        return str(int(quantity))
    return f"{quantity:.2f}"


def _empty_transaction_payload() -> dict[str, Any]:
    """Return a serializable empty transaction for UI display."""
    return Transaction().model_dump()


def _status_message(transaction: Transaction) -> str:
    """Return a human-readable parsing status."""
    if transaction.transaction_type == "unknown":
        return "Could not confidently parse this note. You can still inspect the structured output."
    return f"Parsed as `{transaction.transaction_type}` with confidence `{transaction.confidence:.2f}`."
