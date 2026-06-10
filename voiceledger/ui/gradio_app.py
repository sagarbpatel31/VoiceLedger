"""Gradio application for the VoiceLedger MVP."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from importlib.util import find_spec
from pathlib import Path
from typing import Any

_cache_dir = Path(tempfile.gettempdir()) / "voiceledger-cache"
os.environ.setdefault("MPLCONFIGDIR", str(_cache_dir / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_cache_dir))

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
from voiceledger.ledger.database import (
    add_transaction,
    delete_transaction,
    export_transactions_csv,
    get_transaction,
    get_transactions,
    initialize_database,
    update_transaction,
)
from voiceledger.ledger.inventory import get_inventory
from voiceledger.parser.bulk import REVIEW_COLUMNS, parse_bulk_notes, review_table_to_transactions
from voiceledger.parser.rules import parse_transaction as local_parse_transaction
from voiceledger.parser.schema import Transaction
from voiceledger.reports.pdf_report import generate_daily_summary_pdf
from voiceledger.reports.whatsapp_summary import generate_whatsapp_summary
from voiceledger.speech.transcribe import TranscriptionError, transcribe_audio as local_transcribe_audio


LOW_STOCK_THRESHOLD = 5
TRANSACTION_TYPE_CHOICES = [
    "sale",
    "expense",
    "inventory_purchase",
    "customer_credit",
    "customer_payment",
    "unknown",
]
PAYMENT_STATUS_CHOICES = ["paid", "unpaid", "credit", "unknown"]
DEMO_NOTES = [
    "Bought 60 mangoes",
    "Sold 12 mangoes, 20 each",
    "Sold 8 mangoes, 20 each",
    "Paid 500 for supplies",
    "Amit owes 100",
    "Amit paid 40",
    "Bought 30 onions",
    "rent 300",
]


def create_app(db_path: str | Path | None = None) -> gr.Blocks:
    """Create and return the Gradio Blocks app."""
    initialize_database(db_path)

    with gr.Blocks(title="VoiceLedger", elem_id="voiceledger-app") as demo:
        gr.HTML(
            """
            <section class="vl-hero">
              <h1>VoiceLedger</h1>
              <p>Daily sales, credit, stock, and reports in one working screen.</p>
            </section>
            """
        )

        parsed_state = gr.State(value=None)

        with gr.Group(elem_classes="vl-app-nav"):
            gr.HTML("<strong>Sections</strong>")
            with gr.Row():
                nav_record_button = gr.Button("Record Text & Voice")
                nav_dashboard_button = gr.Button("Dashboard")
                nav_health_button = gr.Button("Demo Health")
                nav_story_button = gr.Button("Submission Story")
                nav_bulk_button = gr.Button("Bulk Import")
                nav_credit_button = gr.Button("Customer Credit")
                nav_inventory_button = gr.Button("Inventory")
                nav_reports_button = gr.Button("Reports & PDF")
                nav_ledger_button = gr.Button("Ledger")

        with gr.Column(visible=True, elem_classes="vl-page-section") as record_page:
                gr.HTML('<div id="vl-page-record" class="vl-page-anchor"></div>')
                gr.HTML(
                    _info_panel(
                        "Hackathon Demo Launchpad",
                        "Use the Sections buttons above to open each workflow page. VoiceLedger is locked for the hackathon demo: core bookkeeping is frozen, with Modal/Nemotron active and local fallback ready.",
                    )
                )
                gr.HTML(_judge_demo_panel())
                with gr.Row():
                    record_seed_demo_button = gr.Button("Seed Demo Transactions", variant="primary")
                    record_health_button = gr.Button("Check Demo Health")
                record_demo_status = gr.Markdown(
                    value="Ready. Click Seed Demo Transactions or Check Demo Health.",
                    elem_classes="vl-status",
                )
                record_health_output = gr.Dataframe(
                    value=_demo_health_placeholder(),
                    headers=["check", "status", "details"],
                    label="Demo health checks",
                    interactive=False,
                    wrap=True,
                    elem_classes="vl-panel",
                )
                gr.HTML(
                    _info_panel(
                        "Workflow",
                        "Record or type -> Parse -> Review -> Save",
                    )
                )
                gr.HTML(
                    """
                    <section class="vl-info-panel">
                      <h2>Example inputs</h2>
                      <p>
                        <span class="vl-chip">Sold 12 mangoes, 20 each</span>
                        <span class="vl-chip">Paid 500 for supplies</span>
                        <span class="vl-chip">Amit owes 100</span>
                        <span class="vl-chip">Bought 50 mangoes</span>
                      </p>
                    </section>
                    """
                )
                with gr.Row(elem_classes="vl-example-row"):
                    example_sale_button = gr.Button("Try sale")
                    example_expense_button = gr.Button("Try expense")
                    example_credit_button = gr.Button("Try credit")
                    example_payment_button = gr.Button("Try payment")
                    example_inventory_button = gr.Button("Try inventory")
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
                    save_button = gr.Button("Save reviewed transaction")

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
                example_sale_button.click(fn=lambda: "Sold 12 mangoes, 20 each", inputs=None, outputs=note_input)
                example_expense_button.click(fn=lambda: "Paid 500 for supplies", inputs=None, outputs=note_input)
                example_credit_button.click(fn=lambda: "Amit owes 100", inputs=None, outputs=note_input)
                example_payment_button.click(fn=lambda: "Amit paid 50", inputs=None, outputs=note_input)
                example_inventory_button.click(fn=lambda: "Bought 50 mangoes", inputs=None, outputs=note_input)

        with gr.Column(visible=False, elem_classes="vl-page-section") as dashboard_page:
                gr.HTML('<div id="vl-page-dashboard" class="vl-page-anchor"></div>')
                gr.HTML(_section_heading("Dashboard"))
                refresh_dashboard_button = gr.Button("Refresh Dashboard", variant="primary")
                with gr.Row(elem_classes="vl-metric-grid"):
                    total_sales_output = gr.HTML()
                    total_expenses_output = gr.HTML()
                    net_profit_output = gr.HTML()
                    outstanding_credit_output = gr.HTML()
                top_selling_item_output = gr.Textbox(label="Top Selling Item", interactive=False)
                with gr.Row():
                    top_items_output = gr.Dataframe(
                        headers=["item", "quantity_sold", "sales_amount"],
                        label="Top Selling Items",
                        interactive=False,
                        wrap=True,
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
                        top_items_output,
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
                        top_items_output,
                        low_stock_output,
                    ],
                )

        with gr.Column(visible=False, elem_classes="vl-page-section") as health_page:
                gr.HTML('<div id="vl-page-health" class="vl-page-anchor"></div>')
                gr.HTML(
                    _info_panel(
                        "Demo Health",
                        "The Space calls Modal first for speech and NVIDIA Nemotron parsing, with local fallback for reliability.",
                    )
                )
                refresh_health_button = gr.Button("Refresh Demo Health", variant="primary")
                health_output = gr.Dataframe(
                    value=_demo_health_placeholder(),
                    headers=["check", "status", "details"],
                    label="System checks",
                    interactive=False,
                    wrap=True,
                    elem_classes="vl-panel",
                )
                health_status_output = gr.Markdown(
                    value="Click Refresh Demo Health to run live checks.",
                    elem_classes="vl-status",
                )
                refresh_health_button.click(
                    fn=lambda: _get_system_check(db_path),
                    inputs=None,
                    outputs=[health_output, health_status_output],
                )
                demo.load(
                    fn=lambda: _get_system_check(db_path),
                    inputs=None,
                    outputs=[health_output, health_status_output],
                )

        with gr.Column(visible=False, elem_classes="vl-page-section") as story_page:
                gr.HTML('<div id="vl-page-story" class="vl-page-anchor"></div>')
                gr.HTML(
                    """
                    <section class="vl-info-panel">
                      <h2>Built for a real informal seller</h2>
                      <p>VoiceLedger is built for a local informal seller who tracks sales, customer dues, stock, and daily profit from short voice notes instead of spreadsheets.</p>
                      <p><strong>Small-model fit:</strong> NVIDIA Nemotron handles messy transaction language through Modal, while deterministic rules keep the bookkeeping path reliable when the model is unavailable.</p>
                      <p><strong>Demo path:</strong> seed demo data, record or type a transaction, save it, then inspect the dashboard, ledger, credit book, inventory, PDF report, WhatsApp summary, and CSV export.</p>
                    </section>
                    """
                )
                seed_demo_button = gr.Button("Seed Demo Transactions", variant="primary")
                seed_demo_status = gr.Markdown(elem_classes="vl-status")

        with gr.Column(visible=False, elem_classes="vl-page-section") as bulk_page:
                gr.HTML('<div id="vl-page-bulk" class="vl-page-anchor"></div>')
                gr.HTML(
                    _info_panel(
                        "Bulk Notes Import",
                        "Paste one transaction per line. Demo examples are in sample_data/demo_transactions.txt.",
                    )
                )
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

        with gr.Column(visible=False, elem_classes="vl-page-section") as credit_page:
                gr.HTML('<div id="vl-page-credit" class="vl-page-anchor"></div>')
                gr.HTML(
                    _info_panel(
                        "Customer Credit Book",
                        "Track outstanding balances from customer credit and payment transactions.",
                    )
                )
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

        with gr.Column(visible=False, elem_classes="vl-page-section") as inventory_page:
                gr.HTML('<div id="vl-page-inventory" class="vl-page-anchor"></div>')
                gr.HTML(
                    _info_panel(
                        "Inventory",
                        "Track stock from inventory purchases and sales. Low-stock rows are highlighted.",
                    )
                )
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

        with gr.Column(visible=False, elem_classes="vl-page-section") as reports_page:
                gr.HTML('<div id="vl-page-reports" class="vl-page-anchor"></div>')
                gr.HTML(
                    _info_panel(
                        "Reports & PDF",
                        "Generate a daily PDF report and a short WhatsApp-ready business summary.",
                    )
                )
                generate_report_button = gr.Button("Generate Daily Summary PDF", variant="primary")
                report_status_output = gr.Markdown(elem_classes="vl-status")
                report_file_output = gr.File(label="Daily Summary PDF", elem_classes="vl-panel")
                generate_report_button.click(
                    fn=lambda: _generate_daily_summary_report(db_path),
                    inputs=None,
                    outputs=[report_file_output, report_status_output],
                )
                gr.HTML(_section_heading("WhatsApp Summary"))
                generate_whatsapp_button = gr.Button("Generate WhatsApp Summary")
                whatsapp_summary_output = gr.Textbox(
                    label="WhatsApp Summary",
                    lines=10,
                    interactive=False,
                    elem_classes="vl-panel",
                    elem_id="whatsapp-summary-output",
                )
                gr.HTML(
                    """
                    <button class="vl-copy-button" type="button" onclick="
                      const root = document.querySelector('#whatsapp-summary-output');
                      const textArea = root ? root.querySelector('textarea') : null;
                      if (textArea && navigator.clipboard) navigator.clipboard.writeText(textArea.value);
                    ">Copy WhatsApp Summary</button>
                    """
                )
                generate_whatsapp_button.click(
                    fn=lambda: generate_whatsapp_summary(
                        db_path=db_path,
                        low_stock_threshold=LOW_STOCK_THRESHOLD,
                    ),
                    inputs=None,
                    outputs=whatsapp_summary_output,
                )

        with gr.Column(visible=False, elem_classes="vl-page-section") as ledger_page:
                gr.HTML('<div id="vl-page-ledger" class="vl-page-anchor"></div>')
                gr.HTML(
                    _info_panel(
                        "Ledger",
                        "Review saved transactions, export CSV, and safely edit or delete individual records.",
                    )
                )
                with gr.Row():
                    refresh_button = gr.Button("Refresh Ledger")
                    export_csv_button = gr.Button("Download CSV")
                export_status_output = gr.Markdown(elem_classes="vl-status")
                csv_file_output = gr.File(label="Transactions CSV", elem_classes="vl-panel")
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
                gr.HTML(_section_heading("Edit or Delete Transaction"))
                with gr.Row():
                    edit_transaction_id = gr.Number(label="Transaction ID", precision=0)
                    load_transaction_button = gr.Button("Load transaction")
                with gr.Row():
                    edit_transaction_type = gr.Dropdown(
                        choices=TRANSACTION_TYPE_CHOICES,
                        label="Transaction type",
                        value="unknown",
                    )
                    edit_payment_status = gr.Dropdown(
                        choices=PAYMENT_STATUS_CHOICES,
                        label="Payment status",
                        value="unknown",
                    )
                with gr.Row():
                    edit_item = gr.Textbox(label="Item")
                    edit_customer = gr.Textbox(label="Customer")
                with gr.Row():
                    edit_quantity = gr.Number(label="Quantity")
                    edit_unit_price = gr.Number(label="Unit price")
                    edit_amount = gr.Number(label="Amount")
                    edit_confidence = gr.Number(label="Confidence")
                edit_notes = gr.Textbox(label="Notes", lines=3)
                with gr.Row():
                    update_transaction_button = gr.Button("Update transaction", variant="primary")
                    delete_transaction_button = gr.Button("Delete transaction")
                edit_status_output = gr.Markdown(elem_classes="vl-status")
                load_transaction_button.click(
                    fn=lambda transaction_id: _load_transaction_for_edit(transaction_id, db_path),
                    inputs=edit_transaction_id,
                    outputs=[
                        edit_transaction_type,
                        edit_item,
                        edit_quantity,
                        edit_unit_price,
                        edit_amount,
                        edit_customer,
                        edit_payment_status,
                        edit_notes,
                        edit_confidence,
                        edit_status_output,
                    ],
                )
                export_csv_button.click(
                    fn=lambda: _export_ledger_csv(db_path),
                    inputs=None,
                    outputs=[csv_file_output, export_status_output],
                )

        save_button.click(
            fn=lambda transaction: _save_transaction_and_refresh(transaction, db_path),
            inputs=parsed_state,
            outputs=[
                status_output,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                top_items_output,
                low_stock_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
            ],
        )
        update_transaction_button.click(
            fn=lambda transaction_id, transaction_type, item, quantity, unit_price, amount, customer, payment_status, notes, confidence: _update_transaction_and_refresh(
                transaction_id,
                transaction_type,
                item,
                quantity,
                unit_price,
                amount,
                customer,
                payment_status,
                notes,
                confidence,
                db_path,
            ),
            inputs=[
                edit_transaction_id,
                edit_transaction_type,
                edit_item,
                edit_quantity,
                edit_unit_price,
                edit_amount,
                edit_customer,
                edit_payment_status,
                edit_notes,
                edit_confidence,
            ],
            outputs=[
                edit_status_output,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                top_items_output,
                low_stock_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
            ],
        )
        delete_transaction_button.click(
            fn=lambda transaction_id: _delete_transaction_and_refresh(transaction_id, db_path),
            inputs=edit_transaction_id,
            outputs=[
                edit_status_output,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                top_items_output,
                low_stock_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
            ],
        )
        seed_demo_button.click(
            fn=lambda: _seed_demo_transactions_and_refresh(db_path),
            inputs=None,
            outputs=[
                seed_demo_status,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                top_items_output,
                low_stock_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
            ],
        )
        record_seed_demo_button.click(
            fn=lambda: _seed_demo_transactions_and_refresh(db_path),
            inputs=None,
            outputs=[
                record_demo_status,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                top_items_output,
                low_stock_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
            ],
        )
        record_health_button.click(
            fn=lambda: _get_system_check(db_path),
            inputs=None,
            outputs=[record_health_output, record_demo_status],
        )
        page_outputs = [
            record_page,
            dashboard_page,
            health_page,
            story_page,
            bulk_page,
            credit_page,
            inventory_page,
            reports_page,
            ledger_page,
        ]
        nav_record_button.click(fn=lambda: _show_page("record"), inputs=None, outputs=page_outputs)
        nav_dashboard_button.click(fn=lambda: _show_page("dashboard"), inputs=None, outputs=page_outputs)
        nav_health_button.click(fn=lambda: _show_page("health"), inputs=None, outputs=page_outputs)
        nav_story_button.click(fn=lambda: _show_page("story"), inputs=None, outputs=page_outputs)
        nav_bulk_button.click(fn=lambda: _show_page("bulk"), inputs=None, outputs=page_outputs)
        nav_credit_button.click(fn=lambda: _show_page("credit"), inputs=None, outputs=page_outputs)
        nav_inventory_button.click(fn=lambda: _show_page("inventory"), inputs=None, outputs=page_outputs)
        nav_reports_button.click(fn=lambda: _show_page("reports"), inputs=None, outputs=page_outputs)
        nav_ledger_button.click(fn=lambda: _show_page("ledger"), inputs=None, outputs=page_outputs)

    return demo


def _info_panel(title: str, body: str) -> str:
    """Return a high-contrast information panel."""
    return f"""
    <section class="vl-info-panel">
      <h2>{title}</h2>
      <p>{body}</p>
    </section>
    """


def _judge_demo_panel() -> str:
    """Return the judge-facing demo flow and backend status line."""
    return """
    <section class="vl-judge-panel">
      <h2>Judge Demo Flow</h2>
      <ol>
        <li><strong>1. Seed demo data</strong><span>Load realistic sales, expense, credit, payment, and stock entries.</span></li>
        <li><strong>2. Record/type</strong><span>Speak or enter a seller note like “Sold 12 mangoes, 20 each”.</span></li>
        <li><strong>3. Save</strong><span>Review the structured transaction and save it to the ledger.</span></li>
        <li><strong>4. View dashboard/reports</strong><span>Open Dashboard, Inventory, Credit, Ledger, PDF, WhatsApp, and CSV.</span></li>
      </ol>
      <p class="vl-health-line">
        Demo Health: Modal backend • NVIDIA Nemotron parser • SQLite ledger • PDF export • configured Modal endpoints
      </p>
    </section>
    """


def _section_heading(title: str) -> str:
    """Return a high-contrast section heading."""
    return f'<h2 class="vl-section-heading">{title}</h2>'


def _show_page(active_page: str) -> tuple[dict[str, Any], ...]:
    """Return Gradio visibility updates for the app pages."""
    page_ids = (
        "record",
        "dashboard",
        "health",
        "story",
        "bulk",
        "credit",
        "inventory",
        "reports",
        "ledger",
    )
    return tuple(gr.update(visible=page_id == active_page) for page_id in page_ids)


def _demo_health_placeholder() -> pd.DataFrame:
    """Return placeholder health rows so the demo health table is never blank."""
    return pd.DataFrame(
        [
            {
                "check": "Modal backend status",
                "status": "Not checked yet",
                "details": "Click Check Demo Health or Refresh Demo Health.",
            },
            {
                "check": "Deployed backend version",
                "status": "Not checked yet",
                "details": "Live Modal /version check appears here.",
            },
            {
                "check": "NVIDIA Nemotron parser",
                "status": "Not checked yet",
                "details": "Model path: nvidia/NVIDIA-Nemotron-3-Nano-4B with local rule fallback.",
            },
            {
                "check": "SQLite database",
                "status": "Not checked yet",
                "details": "Local database availability appears here.",
            },
            {
                "check": "PDF support",
                "status": "Not checked yet",
                "details": "fpdf2 dependency status appears here.",
            },
        ]
    )


def _parse_note(note: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Parse a note and return display data plus serializable state."""
    result = modal_api.parse_transaction_result(note, fallback=local_parse_transaction)
    transaction = result.transaction
    payload = transaction.model_dump()
    status = _status_message(transaction, result.message, result.fallback_reason)
    return payload, payload, status


def _transcribe_and_parse_audio(audio_path: Any) -> tuple[str, dict[str, Any], dict[str, Any] | None, str]:
    """Transcribe recorded audio, parse the transcript, and return UI updates."""
    try:
        transcription = modal_api.transcribe_audio_result(audio_path, fallback=local_transcribe_audio)
    except Exception as exc:
        empty_payload = _empty_transaction_payload()
        return "", empty_payload, None, f"Transcription failed: {exc}"

    parse_result = modal_api.parse_transaction_result(transcription.transcript, fallback=local_parse_transaction)
    transaction = parse_result.transaction
    payload = transaction.model_dump()
    status = _status_message(
        transaction,
        parse_result.message,
        parse_result.fallback_reason,
        prefix=_transcription_status(transcription),
    )
    return transcription.transcript, payload, payload, status


def _save_transaction(transaction_payload: dict[str, Any] | None, db_path: str | Path | None) -> str:
    """Save the parsed transaction payload to SQLite."""
    if not transaction_payload:
        return "Parse a transaction before saving."

    transaction = Transaction(**transaction_payload)
    transaction_id = add_transaction(transaction, db_path)
    return f"Saved transaction #{transaction_id}: {_transaction_summary(transaction)}."


def _save_transaction_and_refresh(
    transaction_payload: dict[str, Any] | None,
    db_path: str | Path | None,
) -> tuple[str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler]:
    """Save a transaction and refresh the demo-critical data views."""
    status = _save_transaction(transaction_payload, db_path)
    return (status, *_refresh_core_views(db_path))


def _load_transaction_for_edit(
    transaction_id: float | int | None,
    db_path: str | Path | None,
) -> tuple[str, str | None, float | None, float | None, float | None, str | None, str, str, float, str]:
    """Load a transaction into editable UI fields."""
    parsed_id = _coerce_transaction_id(transaction_id)
    if parsed_id is None:
        return (
            "unknown",
            None,
            None,
            None,
            None,
            None,
            "unknown",
            "",
            0.0,
            "Enter a transaction id to load.",
        )

    transaction = get_transaction(parsed_id, db_path)
    if transaction is None:
        return (
            "unknown",
            None,
            None,
            None,
            None,
            None,
            "unknown",
            "",
            0.0,
            f"Transaction #{parsed_id} was not found.",
        )

    return (
        transaction.transaction_type,
        transaction.item,
        transaction.quantity,
        transaction.unit_price,
        transaction.amount,
        transaction.customer,
        transaction.payment_status,
        transaction.notes,
        transaction.confidence,
        f"Loaded transaction #{parsed_id}.",
    )


def _update_transaction_and_refresh(
    transaction_id: float | int | None,
    transaction_type: str,
    item: str | None,
    quantity: float | None,
    unit_price: float | None,
    amount: float | None,
    customer: str | None,
    payment_status: str,
    notes: str | None,
    confidence: float | None,
    db_path: str | Path | None,
) -> tuple[str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler]:
    """Update a transaction and refresh all dependent views."""
    parsed_id = _coerce_transaction_id(transaction_id)
    if parsed_id is None:
        return ("Enter a transaction id before updating.", *_refresh_core_views(db_path))

    try:
        transaction = _transaction_from_edit_fields(
            transaction_type=transaction_type,
            item=item,
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
            customer=customer,
            payment_status=payment_status,
            notes=notes,
            confidence=confidence,
        )
    except Exception as exc:
        return (f"Could not update transaction: {exc}", *_refresh_core_views(db_path))

    updated = update_transaction(parsed_id, transaction, db_path)
    if not updated:
        return (f"Transaction #{parsed_id} was not found.", *_refresh_core_views(db_path))
    return (f"Updated transaction #{parsed_id}: {_transaction_summary(transaction)}.", *_refresh_core_views(db_path))


def _delete_transaction_and_refresh(
    transaction_id: float | int | None,
    db_path: str | Path | None,
) -> tuple[str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler]:
    """Delete a transaction and refresh all dependent views."""
    parsed_id = _coerce_transaction_id(transaction_id)
    if parsed_id is None:
        return ("Enter a transaction id before deleting.", *_refresh_core_views(db_path))

    deleted = delete_transaction(parsed_id, db_path)
    if not deleted:
        return (f"Transaction #{parsed_id} was not found.", *_refresh_core_views(db_path))
    return (f"Deleted transaction #{parsed_id} and refreshed balances.", *_refresh_core_views(db_path))


def _export_ledger_csv(db_path: str | Path | None) -> tuple[str, str]:
    """Export ledger transactions to CSV for Gradio download."""
    export_path = export_transactions_csv(db_path)
    return str(export_path), "Transactions CSV is ready."


def _seed_demo_transactions_and_refresh(
    db_path: str | Path | None,
) -> tuple[str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler]:
    """Seed realistic demo transactions and refresh all dependent views."""
    saved_ids = [add_transaction(local_parse_transaction(note), db_path) for note in DEMO_NOTES]
    return (
        f"Seeded {len(saved_ids)} demo transactions. Last transaction id: #{saved_ids[-1]}.",
        *_refresh_core_views(db_path),
    )


def _refresh_core_views(
    db_path: str | Path | None,
) -> tuple[str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler]:
    """Return dashboard, ledger, customer, and inventory refresh values."""
    return (
        *_get_dashboard_data(db_path),
        get_transactions(db_path),
        get_customer_balances(db_path),
        _get_inventory_display(db_path),
    )


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
    """Return business insight values for the Dashboard section."""
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


def _get_system_check(db_path: str | Path | None) -> tuple[pd.DataFrame, str]:
    """Return lightweight health checks for demo readiness."""
    checks: list[dict[str, str]] = []

    modal_health = modal_api.get_modal_health()
    checks.append(
        {
            "check": "Modal backend",
            "status": modal_health["status"],
            "details": f"{modal_health['message']} Version: {modal_health['version']}",
        }
    )
    modal_parse_url = os.getenv(modal_api.MODAL_PARSE_URL_ENV)
    modal_transcribe_url = os.getenv(modal_api.MODAL_TRANSCRIBE_URL_ENV)
    checks.append(
        {
            "check": "NVIDIA Nemotron parser",
            "status": "ok" if modal_parse_url else "fallback",
            "details": "Modal /parse uses nvidia/NVIDIA-Nemotron-3-Nano-4B; local rule parser remains the deterministic fallback.",
        }
    )

    try:
        resolved_db_path = initialize_database(db_path)
        with sqlite3.connect(resolved_db_path) as connection:
            connection.execute("SELECT 1").fetchone()
        checks.append(
            {
                "check": "SQLite database",
                "status": "ok",
                "details": str(resolved_db_path),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "check": "SQLite database",
                "status": "error",
                "details": str(exc),
            }
        )

    fpdf_available = find_spec("fpdf") is not None
    checks.append(
        {
            "check": "PDF export",
            "status": "ok" if fpdf_available else "missing",
            "details": "fpdf2 is installed." if fpdf_available else "Install fpdf2 to enable PDF reports.",
        }
    )

    checks.append(
        {
            "check": "Configured endpoints",
            "status": "ok" if modal_parse_url and modal_transcribe_url else "partial",
            "details": f"parse={'set' if modal_parse_url else 'missing'}, transcribe={'set' if modal_transcribe_url else 'missing'}",
        }
    )

    status = "Demo health checks completed."
    if any(row["status"] in {"error", "missing"} for row in checks):
        status = "Some demo health checks need attention."
    return pd.DataFrame(checks), status


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


def _status_message(
    transaction: Transaction,
    source_message: str = "Parsed transaction.",
    fallback_reason: str | None = None,
    prefix: str | None = None,
) -> str:
    """Return a human-readable parsing status."""
    parts = []
    if prefix:
        parts.append(prefix)
    parts.append(source_message)
    if fallback_reason:
        parts.append(f"Fallback reason: `{fallback_reason}`.")

    if transaction.transaction_type == "unknown":
        parts.append("Could not confidently parse this note. You can still inspect the structured output.")
    else:
        parts.append(f"Parsed as `{transaction.transaction_type}` with confidence `{transaction.confidence:.2f}`.")
    return " ".join(parts)


def _transcription_status(result: modal_api.TranscriptionResult) -> str:
    """Return a concise transcription source status."""
    status = result.message
    if result.fallback_reason:
        status += f" Fallback reason: `{result.fallback_reason}`."
    return status


def _transaction_summary(transaction: Transaction) -> str:
    """Return a concise saved transaction summary."""
    amount = _format_money(transaction.amount or 0) if transaction.amount is not None else "amount not set"
    target = transaction.item or transaction.customer or "transaction"
    return f"{transaction.transaction_type} for {target}, {amount}"


def _coerce_transaction_id(value: float | int | None) -> int | None:
    """Coerce a Gradio number value into a transaction id."""
    if value is None:
        return None
    try:
        transaction_id = int(value)
    except (TypeError, ValueError):
        return None
    if transaction_id <= 0:
        return None
    return transaction_id


def _transaction_from_edit_fields(
    transaction_type: str,
    item: str | None,
    quantity: float | None,
    unit_price: float | None,
    amount: float | None,
    customer: str | None,
    payment_status: str,
    notes: str | None,
    confidence: float | None,
) -> Transaction:
    """Build a Transaction from ledger edit form values."""
    return Transaction(
        transaction_type=transaction_type or "unknown",
        item=_clean_optional_text(item),
        quantity=_clean_optional_float(quantity),
        unit_price=_clean_optional_float(unit_price),
        amount=_clean_optional_float(amount),
        customer=_clean_optional_text(customer),
        payment_status=payment_status or "unknown",
        notes=(notes or "").strip(),
        confidence=0.0 if confidence is None else float(confidence),
    )


def _clean_optional_text(value: str | None) -> str | None:
    """Normalize optional text fields from Gradio inputs."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_optional_float(value: float | int | None) -> float | None:
    """Normalize optional numeric fields from Gradio inputs."""
    if value is None:
        return None
    return float(value)
