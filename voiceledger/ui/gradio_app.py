"""Gradio application for the VoiceLedger MVP."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from html import escape
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
    get_business_summary,
    low_stock_items,
    outstanding_credit,
    top_selling_items,
)
from voiceledger.ui.i18n import t
from backend.modal_api import generate_business_insights
from voiceledger.ledger.customers import get_customer_balances
from voiceledger.ledger.corrections import get_correction_log, record_correction
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
from voiceledger.ledger.settings import get_business_settings, get_low_stock_threshold, update_business_settings
from voiceledger.parser.bulk import REVIEW_COLUMNS, parse_bulk_notes, review_table_to_transactions
from voiceledger.parser.rules import parse_transaction as local_parse_transaction
from voiceledger.parser.schema import Transaction
from voiceledger.reports.actions import generate_customer_followup, generate_reorder_list
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
AI_MODE_CHOICES = ["Cloud AI first", "Local fallback only"]
LANGUAGE_STYLE_CHOICES = [
    "English",
    "English + Hinglish",
    "English + Gujarati-lite",
    "Spanish",
    "French",
    "Portuguese",
    "Multilingual",
]
WHATSAPP_LANGUAGE_CHOICES = ["English", "Spanish", "French", "Portuguese"]
CURRENCY_PRESETS = {
    "India - INR (₹)": "₹",
    "United States - USD ($)": "$",
    "European Union - EUR (€)": "€",
    "United Kingdom - GBP (£)": "£",
    "Mexico - MXN ($)": "$",
    "Brazil - BRL (R$)": "R$",
    "Custom": "",
}
PRICE_MEMORY_BADGE = "Price memory used"
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
        ui_language = gr.State(value="English")
        tts_trigger = gr.Textbox(visible=False, elem_id="vl-tts-trigger")
        tts_trigger.change(
            fn=None,
            js="(text, lang) => { if(text) window.vl_speak(text, lang); return ''; }",
            inputs=[tts_trigger, ui_language],
            outputs=tts_trigger
        )
        tts_output = gr.HTML(
            """
            <div id="vl-tts-container" style="display:none;"></div>
            <script>
              function speak(text, lang) {
                if (!window.speechSynthesis) return;
                const utterance = new SpeechSynthesisUtterance(text);
                const voiceMap = {
                  'English': 'en-US',
                  'Spanish': 'es-ES',
                  'Hindi': 'hi-IN',
                  'French': 'fr-FR',
                  'Portuguese': 'pt-BR'
                };
                utterance.lang = voiceMap[lang] || 'en-US';
                window.speechSynthesis.speak(utterance);
              }
              window.vl_speak = speak;
            </script>
            """,
            visible=True
        )
        
        with gr.Row(elem_classes="vl-lang-selector"):
             lang_dropdown = gr.Dropdown(
                 choices=["English", "Spanish", "Hindi", "French", "Portuguese"],
                 value="English",
                 label="App Language / भाषा",
                 scale=1
             )

        hero_output = gr.HTML(
            f"""
            <section class="vl-hero">
              <h1>{t("app_title", "English")}</h1>
              <p>{t("app_subtitle", "English")}</p>
            </section>
            """
        )

        parsed_state = gr.State(value=None)
        initial_settings = get_business_settings(db_path)

        with gr.Group(elem_classes="vl-app-nav"):
            nav_sections_label = gr.HTML(f"<strong>{t('nav_sections', 'English')}</strong>")
            with gr.Row():
                nav_record_button = gr.Button(t("nav_record", "English"))
                nav_dashboard_button = gr.Button(t("nav_dashboard", "English"))
                nav_health_button = gr.Button(t("nav_health", "English"))
                nav_story_button = gr.Button(t("nav_story", "English"))
                nav_field_test_button = gr.Button(t("nav_field_test", "English"))
                nav_bulk_button = gr.Button(t("nav_bulk", "English"))
                nav_credit_button = gr.Button(t("nav_credit", "English"))
                nav_inventory_button = gr.Button(t("nav_inventory", "English"))
                nav_reports_button = gr.Button(t("nav_reports", "English"))
                nav_ledger_button = gr.Button(t("nav_ledger", "English"))

        def _change_language(lang):
            """Update UI labels and headers when language changes."""
            return (
                lang,
                f"""
                <section class="vl-hero">
                  <h1>{t("app_title", lang)}</h1>
                  <p>{t("app_subtitle", lang)}</p>
                </section>
                """,
                gr.update(value=t("nav_record", lang)),
                gr.update(value=t("nav_dashboard", lang)),
                gr.update(value=t("nav_health", lang)),
                gr.update(value=t("nav_story", lang)),
                gr.update(value=t("nav_field_test", lang)),
                gr.update(value=t("nav_bulk", lang)),
                gr.update(value=t("nav_credit", lang)),
                gr.update(value=t("nav_inventory", lang)),
                gr.update(value=t("nav_reports", lang)),
                gr.update(value=t("nav_ledger", lang)),
                _info_panel(
                    t("nav_sections", lang),
                    t("app_subtitle", lang),
                    language=lang
                ),
                _judge_demo_panel(language=lang),
                _today_work_panel(language=lang),
                _multilingual_examples_panel(language=lang),
                _first_run_onboarding_panel(language=lang),
                gr.update(label=t("record_note", lang)),
                gr.update(label=t("record_audio", lang)),
                gr.update(value=t("parse_text", lang)),
                gr.update(value=t("transcribe_parse", lang)),
                gr.update(value=t("save_transaction", lang)),
                gr.update(label=t("record_image", lang)),
                gr.update(value=t("scan_receipt", lang)),
                f"<strong>{t('nav_sections', lang)}</strong>",
                gr.update(value=t("quick_mango", lang)),
                gr.update(value=t("quick_onion", lang)),
                gr.update(value=t("quick_milk", lang)),
                gr.update(value=t("quick_expense", lang)),
            )

        lang_dropdown.change(
            fn=_change_language,
            inputs=lang_dropdown,
            outputs=[
                ui_language,
                hero_output,
                nav_record_button,
                nav_dashboard_button,
                nav_health_button,
                nav_story_button,
                nav_field_test_button,
                nav_bulk_button,
                nav_credit_button,
                nav_inventory_button,
                nav_reports_button,
                nav_ledger_button,
                record_info_panel,
                judge_panel_output,
                today_work_output,
                examples_panel_output,
                onboarding_panel_output,
                note_input,
                audio_input,
                parse_button,
                transcribe_button,
                save_button,
                image_input,
                scan_button,
                nav_sections_label,
                quick_mango,
                quick_onion,
                quick_milk,
                quick_expense,
            ]
        )

        with gr.Column(visible=True, elem_classes="vl-page-section") as record_page:
                gr.HTML('<div id="vl-page-record" class="vl-page-anchor"></div>')
                record_info_panel = gr.HTML(
                    _info_panel(
                        "Hackathon Demo Launchpad",
                        "Use the Sections buttons above to open each workflow page. VoiceLedger is locked for the hackathon demo: core bookkeeping is frozen, with Modal/Nemotron active and local fallback ready.",
                    )
                )
                onboarding_panel_output = gr.HTML(_first_run_onboarding_panel())
                guided_demo_output = gr.HTML(get_guided_demo_status(db_path))
                refresh_guided_demo_button = gr.Button("Refresh Guided Judge Mode")
                
                gr.HTML(_section_heading("Quick Actions"))
                with gr.Row(elem_classes="vl-quick-action-row"):
                    quick_mango = gr.Button(t("quick_mango", "English"))
                    quick_onion = gr.Button(t("quick_onion", "English"))
                    quick_milk = gr.Button(t("quick_milk", "English"))
                    quick_expense = gr.Button(t("quick_expense", "English"))

                command_center_output = gr.HTML(_command_center(db_path))
                gr.HTML(_section_heading("Seller Setup"))
                with gr.Row():
                    business_name_input = gr.Textbox(
                        label="Business name",
                        value=initial_settings["business_name"],
                        elem_classes="vl-panel",
                    )
                    currency_preset_input = gr.Dropdown(
                        choices=list(CURRENCY_PRESETS.keys()),
                        label="Currency preset",
                        value=_currency_preset_for_symbol(initial_settings["currency_symbol"]),
                        elem_classes="vl-panel",
                    )
                    currency_symbol_input = gr.Textbox(
                        label="Currency label",
                        value=initial_settings["currency_symbol"],
                        elem_classes="vl-panel",
                    )
                currency_preset_input.change(
                    fn=_currency_symbol_for_preset,
                    inputs=currency_preset_input,
                    outputs=currency_symbol_input,
                )
                with gr.Row():
                    low_stock_threshold_input = gr.Number(
                        label="Low-stock threshold",
                        value=float(initial_settings["low_stock_threshold"]),
                        elem_classes="vl-panel",
                    )
                    language_style_input = gr.Dropdown(
                        choices=LANGUAGE_STYLE_CHOICES,
                        label="Primary language style",
                        value=initial_settings["language_style"],
                    )
                save_settings_button = gr.Button("Save Seller Setup")
                settings_status_output = gr.Markdown(
                    value=_seller_setup_status(initial_settings),
                    elem_classes="vl-status",
                )
                gr.HTML(_section_heading("AI Mode"))
                with gr.Row():
                    ai_mode_input = gr.Dropdown(
                        choices=AI_MODE_CHOICES,
                        label="Parser and speech mode",
                        value="Cloud AI first",
                        elem_classes="vl-panel",
                    )
                    ai_mode_status_output = gr.HTML(_ai_mode_status("Cloud AI first"))
                ai_mode_input.change(fn=_ai_mode_status, inputs=ai_mode_input, outputs=ai_mode_status_output)
                judge_panel_output = gr.HTML(_judge_demo_panel())
                today_work_output = gr.HTML(_today_work_panel())
                start_today_button = gr.Button("Start Today", variant="primary")
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
                refresh_guided_demo_button.click(
                    fn=lambda: get_guided_demo_status(db_path),
                    inputs=None,
                    outputs=guided_demo_output,
                )
                gr.HTML(
                    _info_panel(
                        "Workflow",
                        "Record or type -> Parse -> Review -> Save",
                    )
                )
                examples_panel_output = gr.HTML(
                    _multilingual_examples_panel()
                )
                gr.HTML(_section_heading("Voice Command Shortcuts"))
                with gr.Row():
                    command_input = gr.Textbox(
                        label="Command",
                        placeholder="close today, show Amit, stock mangoes",
                        elem_classes="vl-panel",
                    )
                    command_button = gr.Button("Run Command")
                command_output = gr.HTML(_empty_detail_card("Command result", "Try close today, show Amit, or stock mangoes."))
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
                    with gr.Column():
                        image_input = gr.Image(
                            label="Upload receipt image",
                            sources=["upload", "webcam"],
                            type="filepath",
                            elem_classes="vl-panel",
                        )
                        scan_button = gr.Button("Scan Receipt", variant="primary")

                review_card_output = gr.HTML(_empty_review_card())
                gr.HTML(_section_heading("Edit Before Save"))
                with gr.Row():
                    review_transaction_type = gr.Dropdown(
                        choices=TRANSACTION_TYPE_CHOICES,
                        label="Transaction type",
                        value="unknown",
                    )
                    review_payment_status = gr.Dropdown(
                        choices=PAYMENT_STATUS_CHOICES,
                        label="Payment status",
                        value="unknown",
                    )
                with gr.Row():
                    review_item = gr.Textbox(label="Item")
                    review_customer = gr.Textbox(label="Customer")
                with gr.Row():
                    review_quantity = gr.Number(label="Quantity")
                    review_unit_price = gr.Number(label="Unit price")
                    review_amount = gr.Number(label="Amount")
                    review_confidence = gr.Number(label="Confidence")
                review_notes = gr.Textbox(label="Notes", lines=2)
                with gr.Row():
                    apply_review_edits_button = gr.Button("Update Review")
                    save_button = gr.Button("Save reviewed transaction", variant="primary")
                receipt_output = gr.HTML(_empty_receipt_card())
                with gr.Row():
                    add_another_button = gr.Button("Add another")
                    view_dashboard_button = gr.Button("View dashboard")
                    download_summary_button = gr.Button("Download summary")
                structured_output = gr.JSON(label="Technical structured output", elem_classes="vl-panel", visible=False)
                status_output = gr.Markdown(elem_classes="vl-status")

                parse_button.click(
                    fn=lambda note, ai_mode: _parse_note_for_editing(note, db_path, ai_mode),
                    inputs=[note_input, ai_mode_input],
                    outputs=[
                        structured_output,
                        parsed_state,
                        status_output,
                        review_card_output,
                        review_transaction_type,
                        review_item,
                        review_quantity,
                        review_unit_price,
                        review_amount,
                        review_customer,
                        review_payment_status,
                        review_notes,
                        review_confidence,
                    ],
                )
                transcribe_button.click(
                    fn=lambda audio_path, ai_mode: _transcribe_and_parse_audio_for_editing(audio_path, db_path, ai_mode),
                    inputs=[audio_input, ai_mode_input],
                    outputs=[
                        transcript_output,
                        structured_output,
                        parsed_state,
                        status_output,
                        review_card_output,
                        review_transaction_type,
                        review_item,
                        review_quantity,
                        review_unit_price,
                        review_amount,
                        review_customer,
                        review_payment_status,
                        review_notes,
                        review_confidence,
                    ],
                )
                scan_button.click(
                    fn=lambda image_path, ai_mode: _scan_receipt_for_editing(image_path, db_path, ai_mode),
                    inputs=[image_input, ai_mode_input],
                    outputs=[
                        structured_output,
                        parsed_state,
                        status_output,
                        review_card_output,
                        review_item,
                        review_quantity,
                        review_unit_price,
                        review_amount,
                        review_customer,
                        review_transaction_type,
                        review_payment_status,
                        review_confidence,
                        review_notes,
                    ],
                )
                example_sale_button.click(fn=lambda: "Sold 12 mangoes, 20 each", inputs=None, outputs=note_input)
                example_expense_button.click(fn=lambda: "Paid 500 for supplies", inputs=None, outputs=note_input)
                example_credit_button.click(fn=lambda: "Amit owes 100", inputs=None, outputs=note_input)
                example_payment_button.click(fn=lambda: "Amit paid 50", inputs=None, outputs=note_input)
                example_inventory_button.click(fn=lambda: "Bought 50 mangoes", inputs=None, outputs=note_input)
                start_today_button.click(
                    fn=lambda: ("Sold 12 mangoes, 20 each", "Start by typing or recording one transaction, then parse and review it."),
                    inputs=None,
                    outputs=[note_input, record_demo_status],
                )
                command_button.click(
                    fn=lambda command: _run_voice_command(command, db_path),
                    inputs=command_input,
                    outputs=command_output,
                )
                apply_review_edits_button.click(
                    fn=lambda parsed, transaction_type, item, quantity, unit_price, amount, customer, payment_status, notes, confidence: _apply_review_edits(
                        parsed,
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
                        parsed_state,
                        review_transaction_type,
                        review_item,
                        review_quantity,
                        review_unit_price,
                        review_amount,
                        review_customer,
                        review_payment_status,
                        review_notes,
                        review_confidence,
                    ],
                    outputs=[structured_output, parsed_state, status_output, review_card_output],
                )

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
                timeline_output = gr.LinePlot(
                    x="date",
                    y="amount",
                    color="kind",
                    title="Sales and Expenses Timeline",
                    x_title="Date",
                    y_title="Amount",
                    height=260,
                    elem_classes="vl-panel",
                )
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
                insight_coach_output = gr.HTML(_insight_coach(db_path, language="English"))
                seller_day_output = gr.HTML(_seller_day_timeline(db_path))
                refresh_dashboard_button.click(
                    fn=lambda lang: _get_dashboard_data(db_path, language=lang),
                    inputs=[ui_language],
                    outputs=[
                        total_sales_output,
                        total_expenses_output,
                        net_profit_output,
                        outstanding_credit_output,
                        top_selling_item_output,
                        timeline_output,
                        top_items_output,
                        low_stock_output,
                        insight_coach_output,
                        seller_day_output,
                    ],
                )
                demo.load(
                    fn=lambda lang: _get_dashboard_data(db_path, language=lang),
                    inputs=[ui_language],
                    outputs=[
                        total_sales_output,
                        total_expenses_output,
                        net_profit_output,
                        outstanding_credit_output,
                        top_selling_item_output,
                        timeline_output,
                        top_items_output,
                        low_stock_output,
                        insight_coach_output,
                        seller_day_output,
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
                gr.HTML(_submission_story_panel())
                gr.HTML(_ai_pipeline_strip())
                gr.HTML(_small_model_fit_card())
                gr.HTML(_section_heading("Field Test Notes"))
                with gr.Row():
                    field_who_input = gr.Textbox(
                        label="Who this is for",
                        value=initial_settings["field_test_who"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                    field_tried_input = gr.Textbox(
                        label="What they tried",
                        value=initial_settings["field_test_tried"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                    field_changed_input = gr.Textbox(
                        label="What changed after feedback",
                        value=initial_settings["field_test_changed"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                with gr.Row():
                    field_pain_point_input = gr.Textbox(
                        label="Pain point",
                        value=initial_settings["field_pain_point"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                    field_before_input = gr.Textbox(
                        label="Before VoiceLedger",
                        value=initial_settings["field_before"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                with gr.Row():
                    field_after_input = gr.Textbox(
                        label="After VoiceLedger",
                        value=initial_settings["field_after"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                    field_useful_input = gr.Textbox(
                        label="Useful moments",
                        value=initial_settings["field_useful_moments"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                save_field_notes_button = gr.Button("Save Field Test Notes")
                field_notes_status_output = gr.Markdown(elem_classes="vl-status")
                seed_demo_button = gr.Button("Seed Demo Transactions", variant="primary")
                seed_demo_status = gr.Markdown(elem_classes="vl-status")

        with gr.Column(visible=False, elem_classes="vl-page-section") as field_test_page:
                gr.HTML('<div id="vl-page-field-test" class="vl-page-anchor"></div>')
                gr.HTML(
                    _info_panel(
                        "Field Test Mode",
                        "Use this with a real seller or a realistic practice run. Capture what they tried, what failed, and what changed after feedback.",
                    )
                )
                field_test_checklist = gr.CheckboxGroup(
                    choices=[
                        "Record sale",
                        "Record expense",
                        "Customer owes",
                        "Customer paid",
                        "Bought stock",
                        "Review dashboard",
                        "Export report",
                    ],
                    label="Seller test checklist",
                    value=_field_test_checklist_values(initial_settings),
                    elem_classes="vl-panel",
                )
                with gr.Row():
                    field_test_who_input = gr.Textbox(
                        label="Who this is for",
                        value=initial_settings["field_test_who"],
                        lines=4,
                        elem_classes="vl-panel",
                    )
                    field_test_tried_input = gr.Textbox(
                        label="What they tried",
                        value=initial_settings["field_test_tried"],
                        lines=4,
                        elem_classes="vl-panel",
                    )
                    field_test_changed_input = gr.Textbox(
                        label="What changed after feedback",
                        value=initial_settings["field_test_changed"],
                        lines=4,
                        elem_classes="vl-panel",
                    )
                with gr.Row():
                    field_test_pain_point_input = gr.Textbox(
                        label="Pain point",
                        value=initial_settings["field_pain_point"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                    field_test_before_input = gr.Textbox(
                        label="Before VoiceLedger",
                        value=initial_settings["field_before"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                with gr.Row():
                    field_test_after_input = gr.Textbox(
                        label="After VoiceLedger",
                        value=initial_settings["field_after"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                    field_test_useful_input = gr.Textbox(
                        label="Useful moments",
                        value=initial_settings["field_useful_moments"],
                        lines=3,
                        elem_classes="vl-panel",
                    )
                field_test_changed_after_feedback_input = gr.Textbox(
                    label="Changed after feedback",
                    value=initial_settings["field_changed_after_feedback"],
                    lines=3,
                    elem_classes="vl-panel",
                )
                save_field_test_button = gr.Button("Save Field Test Evidence", variant="primary")
                field_test_status_output = gr.Markdown(
                    value=_field_test_summary(initial_settings),
                    elem_classes="vl-status",
                )
                gr.HTML(_section_heading("Mistake Log"))
                refresh_corrections_button = gr.Button("Refresh Correction Log")
                correction_log_output = gr.Dataframe(
                    value=get_correction_log(db_path),
                    headers=["id", "changed_fields", "original_payload", "corrected_payload", "created_at"],
                    label="Corrections made before save",
                    interactive=False,
                    wrap=True,
                    elem_classes="vl-panel",
                )
                refresh_corrections_button.click(
                    fn=lambda: get_correction_log(db_path),
                    inputs=None,
                    outputs=correction_log_output,
                )

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
                gr.HTML(_section_heading("Customer Detail"))
                with gr.Row():
                    customer_detail_name = gr.Textbox(label="Customer name", placeholder="Amit")
                    customer_detail_button = gr.Button("Show customer detail")
                customer_detail_summary = gr.HTML(_empty_detail_card("Customer detail"))
                customer_detail_output = gr.Dataframe(
                    headers=["id", "transaction_type", "amount", "notes", "created_at"],
                    label="Customer transactions",
                    interactive=False,
                    wrap=True,
                    elem_classes="vl-panel",
                )
                customer_detail_button.click(
                    fn=lambda customer_name: _get_customer_detail(customer_name, db_path),
                    inputs=customer_detail_name,
                    outputs=[customer_detail_summary, customer_detail_output],
                )
                gr.HTML(_section_heading("Customer Follow-up"))
                followup_customer_name = gr.Textbox(label="Customer for WhatsApp reminder", placeholder="Amit")
                followup_button = gr.Button("Generate Follow-up Message")
                followup_output = gr.Textbox(
                    label="WhatsApp follow-up",
                    lines=4,
                    interactive=False,
                    elem_classes="vl-panel",
                )
                followup_button.click(
                    fn=lambda customer_name: generate_customer_followup(customer_name, db_path),
                    inputs=followup_customer_name,
                    outputs=followup_output,
                )
                gr.HTML(_section_heading("Debt Reminder Queue"))
                refresh_debt_queue_button = gr.Button("Refresh Reminder Queue")
                debt_queue_output = gr.Dataframe(
                    value=get_debt_reminder_queue(db_path),
                    headers=["customer", "outstanding_balance", "suggested_message"],
                    label="Customers to follow up",
                    interactive=False,
                    wrap=True,
                    elem_classes="vl-panel",
                )
                refresh_debt_queue_button.click(
                    fn=lambda: get_debt_reminder_queue(db_path),
                    inputs=None,
                    outputs=debt_queue_output,
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
                gr.HTML(_section_heading("Inventory Detail"))
                with gr.Row():
                    inventory_detail_item = gr.Textbox(label="Item", placeholder="mangoes")
                    inventory_detail_button = gr.Button("Show inventory detail")
                inventory_detail_summary = gr.HTML(_empty_detail_card("Inventory detail"))
                inventory_detail_output = gr.Dataframe(
                    headers=["id", "transaction_type", "quantity", "amount", "notes", "created_at"],
                    label="Item movement",
                    interactive=False,
                    wrap=True,
                    elem_classes="vl-panel",
                )
                inventory_detail_button.click(
                    fn=lambda item: _get_inventory_detail(item, db_path),
                    inputs=inventory_detail_item,
                    outputs=[inventory_detail_summary, inventory_detail_output],
                )
                gr.HTML(_section_heading("Inventory Reorder List"))
                reorder_button = gr.Button("Generate Reorder List")
                reorder_output = gr.Dataframe(
                    headers=["item", "current_stock", "recent_sold", "threshold", "status", "suggested_action"],
                    label="Inventory reorder intelligence",
                    interactive=False,
                    wrap=True,
                    elem_classes="vl-panel",
                )
                reorder_message_output = gr.Textbox(
                    label="WhatsApp restock message",
                    lines=8,
                    interactive=False,
                    elem_classes="vl-panel",
                )
                reorder_button.click(
                    fn=lambda: _generate_reorder_intelligence_for_ui(db_path),
                    inputs=None,
                    outputs=[reorder_output, reorder_message_output],
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
                gr.HTML(_section_heading("Daily Closeout"))
                closeout_button = gr.Button("Run Daily Closeout", variant="primary")
                closeout_summary_output = gr.HTML(_empty_detail_card("Daily closeout"))
                with gr.Row():
                    closeout_pdf_output = gr.File(label="Closeout PDF", elem_classes="vl-panel")
                    closeout_csv_output = gr.File(label="Closeout CSV", elem_classes="vl-panel")
                closeout_whatsapp_output = gr.Textbox(
                    label="Closeout WhatsApp Summary",
                    lines=8,
                    interactive=False,
                    elem_classes="vl-panel",
                )
                closeout_status_output = gr.Markdown(elem_classes="vl-status")
                closeout_button.click(
                    fn=lambda: _run_daily_closeout(db_path),
                    inputs=None,
                    outputs=[closeout_summary_output, closeout_pdf_output, closeout_csv_output, closeout_whatsapp_output, closeout_status_output],
                )
                gr.HTML(_section_heading("WhatsApp Summary"))
                generate_whatsapp_button = gr.Button("Generate WhatsApp Summary")
                whatsapp_language_input = gr.Dropdown(
                    choices=WHATSAPP_LANGUAGE_CHOICES,
                    label="Summary language",
                    value="English",
                    elem_classes="vl-panel",
                )
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
                    fn=lambda language: _generate_whatsapp_summary(db_path, language),
                    inputs=whatsapp_language_input,
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
            fn=lambda parsed, transaction_type, item, quantity, unit_price, amount, customer, payment_status, notes, confidence, lang: _save_reviewed_transaction_and_refresh(
                parsed,
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
                language=lang,
            ),
            inputs=[
                parsed_state,
                review_transaction_type,
                review_item,
                review_quantity,
                review_unit_price,
                review_amount,
                review_customer,
                review_payment_status,
                review_notes,
                review_confidence,
                ui_language,
            ],
            outputs=[
                status_output,
                receipt_output,
                command_center_output,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                timeline_output,
                top_items_output,
                low_stock_output,
                insight_coach_output,
                seller_day_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
                tts_trigger,
            ],
        )
        update_transaction_button.click(
            fn=lambda transaction_id, transaction_type, item, quantity, unit_price, amount, customer, payment_status, notes, confidence, lang: _update_transaction_and_refresh(
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
                language=lang,
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
                ui_language,
            ],
            outputs=[
                edit_status_output,
                command_center_output,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                timeline_output,
                top_items_output,
                low_stock_output,
                insight_coach_output,
                seller_day_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
                tts_trigger,
            ],
        )
        delete_transaction_button.click(
            fn=lambda transaction_id, lang: _delete_transaction_and_refresh(transaction_id, db_path, language=lang),
            inputs=[edit_transaction_id, ui_language],
            outputs=[
                edit_status_output,
                command_center_output,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                timeline_output,
                top_items_output,
                low_stock_output,
                insight_coach_output,
                seller_day_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
                tts_trigger,
            ],
        )
        seed_demo_button.click(
            fn=lambda lang: _seed_demo_transactions_and_refresh(db_path, language=lang),
            inputs=[ui_language],
            outputs=[
                seed_demo_status,
                command_center_output,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                timeline_output,
                top_items_output,
                low_stock_output,
                insight_coach_output,
                seller_day_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
                tts_trigger,
            ],
        )
        record_seed_demo_button.click(
            fn=lambda lang: _seed_demo_transactions_and_refresh(db_path, language=lang),
            inputs=[ui_language],
            outputs=[
                record_demo_status,
                command_center_output,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                timeline_output,
                top_items_output,
                low_stock_output,
                insight_coach_output,
                seller_day_output,
                ledger_output,
                customer_balances_output,
                inventory_output,
                tts_trigger,
            ],
        )
        save_settings_button.click(
            fn=lambda business_name, currency_symbol, low_stock_threshold, language_style: _save_seller_setup_and_refresh(
                business_name,
                currency_symbol,
                low_stock_threshold,
                language_style,
                db_path,
            ),
            inputs=[business_name_input, currency_symbol_input, low_stock_threshold_input, language_style_input],
            outputs=[
                settings_status_output,
                command_center_output,
                total_sales_output,
                total_expenses_output,
                net_profit_output,
                outstanding_credit_output,
                top_selling_item_output,
                timeline_output,
                top_items_output,
                low_stock_output,
                insight_coach_output,
                seller_day_output,
                inventory_output,
            ],
        )
        save_field_notes_button.click(
            fn=lambda who, tried, changed, pain_point, before, after, useful: _save_field_notes(
                who,
                tried,
                changed,
                db_path,
                pain_point=pain_point,
                before=before,
                after=after,
                useful=useful,
            ),
            inputs=[
                field_who_input,
                field_tried_input,
                field_changed_input,
                field_pain_point_input,
                field_before_input,
                field_after_input,
                field_useful_input,
            ],
            outputs=field_notes_status_output,
        )
        save_field_test_button.click(
            fn=lambda checklist, who, tried, changed, pain_point, before, after, useful, changed_after_feedback: _save_field_test_evidence(
                checklist,
                who,
                tried,
                changed,
                db_path,
                pain_point=pain_point,
                before=before,
                after=after,
                useful=useful,
                changed_after_feedback=changed_after_feedback,
            ),
            inputs=[
                field_test_checklist,
                field_test_who_input,
                field_test_tried_input,
                field_test_changed_input,
                field_test_pain_point_input,
                field_test_before_input,
                field_test_after_input,
                field_test_useful_input,
                field_test_changed_after_feedback_input,
            ],
            outputs=field_test_status_output,
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
            field_test_page,
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
        nav_field_test_button.click(fn=lambda: _show_page("field_test"), inputs=None, outputs=page_outputs)
        nav_bulk_button.click(fn=lambda: _show_page("bulk"), inputs=None, outputs=page_outputs)
        nav_credit_button.click(fn=lambda: _show_page("credit"), inputs=None, outputs=page_outputs)
        nav_inventory_button.click(fn=lambda: _show_page("inventory"), inputs=None, outputs=page_outputs)
        nav_reports_button.click(fn=lambda: _show_page("reports"), inputs=None, outputs=page_outputs)
        nav_ledger_button.click(fn=lambda: _show_page("ledger"), inputs=None, outputs=page_outputs)
        add_another_button.click(
            fn=_reset_record_form,
            inputs=None,
            outputs=[
                note_input,
                transcript_output,
                structured_output,
                parsed_state,
                status_output,
                review_card_output,
                receipt_output,
                review_transaction_type,
                review_item,
                review_quantity,
                review_unit_price,
                review_amount,
                review_customer,
                review_payment_status,
                review_notes,
                review_confidence,
            ],
        )
        view_dashboard_button.click(fn=lambda: _show_page("dashboard"), inputs=None, outputs=page_outputs)
        download_summary_button.click(
            fn=lambda: _generate_daily_summary_report(db_path),
            inputs=None,
            outputs=[report_file_output, report_status_output],
        )

    return demo


def _info_panel(title: str, body: str, language: str = "English") -> str:
    """Return a high-contrast information panel."""
    tech_note = "Receipt scanning uses <strong>Moondream-2 (1.6B VLM)</strong> optimized for structured extraction on small compute."
    if language == "Spanish":
        tech_note = "El escaneo de recibos utiliza <strong>Moondream-2 (1.6B VLM)</strong> optimizado para la extracción estructurada."
    elif language == "Hindi":
        tech_note = "रसीद स्कैनिंग <strong>Moondream-2 (1.6B VLM)</strong> का उपयोग करती है, जो छोटे कंप्यूट पर संरचित निष्कर्षण के लिए अनुकूलित है।"

    return f"""
    <section class="vl-info-panel">
      <h2>{title}</h2>
      <p>{body}</p>
      <div style="margin-top: 10px; font-size: 0.85em; opacity: 0.8;">
        <strong>Tech Note:</strong> {tech_note}
      </div>
    </section>
    """


def _judge_demo_panel(language: str = "English") -> str:
    """Return the judge-facing demo flow and backend status line."""
    title = "Judge Demo Flow"
    health_line = "Demo Health: Modal backend • NVIDIA Nemotron parser • SQLite ledger • PDF export • configured Modal endpoints"
    
    steps = [
        ("1. Seed demo data", "Load realistic sales, expense, credit, payment, and stock entries."),
        ("2. Record/type", "Speak or enter a seller note like “Sold 12 mangoes, 20 each”."),
        ("3. Save", "Review the structured transaction and save it to the ledger."),
        ("4. View dashboard/reports", "Open Dashboard, Inventory, Credit, Ledger, PDF, WhatsApp, and CSV.")
    ]

    if language == "Spanish":
        title = "Flujo de Demo para Jueces"
        health_line = "Salud de la Demo: Backend Modal • Analizador NVIDIA Nemotron • Libro SQLite • Exportación PDF • Endpoints Modal configurados"
        steps = [
            ("1. Cargar datos", "Carga registros realistas de ventas, gastos, crédito, pagos y stock."),
            ("2. Grabar/escribir", "Habla o escribe una nota como \"Vendí 12 mangos, 20 cada uno\"."),
            ("3. Guardar", "Revisa la transacción estructurada y guárdala en el libro mayor."),
            ("4. Ver reportes", "Abre Tablero, Inventario, Crédito, Libro Mayor, PDF, WhatsApp y CSV.")
        ]
    elif language == "Hindi":
        title = "जज डेमो फ्लो"
        health_line = "डेमो हेल्थ: मॉडल बैकएंड • NVIDIA Nemotron पार्सर • SQLite लेजर • PDF एक्सपोर्ट • कॉन्फ़िगर किए गए मॉडल एंडपॉइंट"
        steps = [
            ("1. डेमो डेटा लोड करें", "यथार्थवादी बिक्री, व्यय, क्रेडिट, भुगतान और स्टॉक प्रविष्टियां लोड करें।"),
            ("2. रिकॉर्ड/टाइप करें", "विक्रेता नोट बोलें या दर्ज करें जैसे \"12 आम बेचे, 20 प्रत्येक\"।"),
            ("3. सहेजें", "संरचित लेनदेन की समीक्षा करें और इसे लेजर में सहेजें।"),
            ("4. डैशबोर्ड/रिपोर्ट देखें", "डैशबोर्ड, इन्वेंट्री, क्रेडिट, लेजर, PDF, व्हाट्सएप और CSV खोलें।")
        ]

    rows = "".join(f"<li><strong>{s[0]}</strong><span>{s[1]}</span></li>" for s in steps)
    
    return f"""
    <section class="vl-judge-panel">
      <h2>{title}</h2>
      <ol>{rows}</ol>
      <p class="vl-health-line">{health_line}</p>
    </section>
    """


def _today_work_panel(language: str = "English") -> str:
    """Return guided daily action suggestions."""
    title = t("start_today", language)
    if language == "English": title = "Today's Work"

    items = [
        ("Record Sale", "“Sold 12 mangoes, 20 each”"),
        ("Record Expense", "“Paid 500 for supplies”"),
        ("Customer Owes", "“Amit owes 100”"),
        ("Customer Paid", "“Amit paid 50”"),
        ("Bought Stock", "“Bought 50 mangoes”")
    ]

    if language == "Spanish":
        items = [
            ("Venta", "\"Vendí 12 mangos, 20 cada uno\""),
            ("Gasto", "\"Pagué 500 por suministros\""),
            ("Cliente debe", "\"Amit debe 100\""),
            ("Cliente pagó", "\"Amit pagó 50\""),
            ("Compra Stock", "\"Compré 50 mangos\"")
        ]
    elif language == "Hindi":
        items = [
            ("बिक्री", "\"12 आम बेचे, 20 प्रत्येक\""),
            ("व्यय", "\"आपूर्ति के लिए 500 का भुगतान किया\""),
            ("ग्राहक बकाया", "\"अमित के 100 बकाया हैं\""),
            ("ग्राहक भुगतान", "\"अमित ने 50 का भुगतान किया\""),
            ("स्टॉक खरीदा", "\"50 आम खरीदे\"")
        ]

    rows = "".join(f"<span><strong>{i[0]}</strong>{i[1]}</span>" for i in items)
    return f"""
    <section class="vl-today-panel">
      <h2>{title}</h2>
      <div>{rows}</div>
    </section>
    """


def _first_run_onboarding_panel(language: str = "English") -> str:
    """Return a compact first-run guide for sellers."""
    title = "Start in 60 seconds"
    steps = [
        ("1. Confirm setup", "Business name, currency, stock threshold, and language style."),
        ("2. Record one note", "Use voice or text for a sale, expense, customer due, payment, or stock purchase."),
        ("3. Review and fix", "Edit item, amount, customer, or type before saving."),
        ("4. Close the day", "Open Dashboard, Field Test, Reports, and Ledger to inspect results.")
    ]

    if language == "Spanish":
        title = "Comienza en 60 segundos"
        steps = [
            ("1. Confirmar config", "Nombre, moneda, umbral de stock y estilo de idioma."),
            ("2. Grabar nota", "Voz o texto para venta, gasto, crédito, pago o compra de stock."),
            ("3. Revisar y fijar", "Edita el artículo, monto, cliente o tipo antes de guardar."),
            ("4. Cerrar el día", "Abre Tablero, Pruebas, Informes y Libro Mayor para ver resultados.")
        ]
    elif language == "Hindi":
        title = "60 सेकंड में शुरू करें"
        steps = [
            ("1. सेटअप पुष्टि करें", "व्यवसाय का नाम, मुद्रा, स्टॉक सीमा और भाषा शैली।"),
            ("2. एक नोट रिकॉर्ड करें", "बिक्री, व्यय, ग्राहक बकाया, भुगतान या स्टॉक खरीद के लिए आवाज या टेक्स्ट का उपयोग करें।"),
            ("3. समीक्षा और सुधार", "सहेजने से पहले आइटम, राशि, ग्राहक या प्रकार संपादित करें।"),
            ("4. दिन समाप्त करें", "परिणामों का निरीक्षण करने के लिए डैशबोर्ड, फील्ड टेस्ट, रिपोर्ट और लेजर खोलें।")
        ]

    rows = "".join(f"<li><strong>{s[0]}</strong><span>{s[1]}</span></li>" for s in steps)
    return f"""
    <section class="vl-onboarding-panel">
      <h2>{title}</h2>
      <ol>{rows}</ol>
    </section>
    """


def _multilingual_examples_panel(language: str = "English") -> str:
    """Return grouped examples across English and local seller shorthand."""
    title = "Example inputs"
    if language == "Spanish": title = "Ejemplos de entrada"
    elif language == "Hindi": title = "इनपुट उदाहरण"

    return f"""
    <section class="vl-language-panel">
      <h2>{title}</h2>
      <div>
        <span><strong>English</strong><code>Sold 12 mangoes, 20 each</code><code>Paid 500 for supplies</code><code>Amit owes 100</code></span>
        <span><strong>Hinglish</strong><code>Amit ne 100 dene hai</code><code>Amit ne 50 diya</code><code>50 mango kharida</code></span>
        <span><strong>Gujarati-lite</strong><code>50 mango lidha</code><code>rent 300 diya</code><code>12 mango 20 each</code></span>
        <span><strong>Spanish</strong><code>Vendí 12 mangos, 20 cada uno</code><code>Pagué 500 por suministros</code><code>Amit debe 100</code></span>
        <span><strong>French</strong><code>Vendu 12 mangues, 20 chacun</code><code>Payé 500 pour fournitures</code><code>Amit doit 100</code></span>
        <span><strong>Portuguese</strong><code>Vendi 12 mangas, 20 cada</code><code>Paguei 500 por suprimentos</code><code>Amit deve 100</code></span>
      </div>
    </section>
    """


def _submission_story_panel() -> str:
    """Return the judge-facing story summary for the Submission Story page."""
    return """
    <section class="vl-info-panel">
      <h2>Built for a real informal seller</h2>
      <p>VoiceLedger is built for a local informal seller who tracks sales, customer dues, stock, and daily profit from short voice notes instead of spreadsheets.</p>
      <p><strong>The "Backyard" Story:</strong> Imagine a market vendor in a busy stall. They don't have time to type. They might have a cheap phone and spotty internet. We use <strong>Small AI</strong> to ensure they can track their business without high costs or complex interfaces.</p>
      <p><strong>The "Build Small" Advantage:</strong>
        <ul>
          <li><strong>Local-First Resilience:</strong> If the "backyard" has no internet, VoiceLedger falls back to a deterministic rule-engine, ensuring the business never stops.</li>
          <li><strong>Efficiency:</strong> Using 4B LLMs and 1.6B VLMs means faster response times and lower costs ($0.001 per transaction).</li>
          <li><strong>Empathy:</strong> Voice-first, multilingual, and QR-ready for immediate real-world utility.</li>
        </ul>
      </p>
      <p><strong>Demo path:</strong> seed demo data, record or type a transaction, review warnings, save it, then inspect the dashboard, ledger, credit book, inventory, PDF report, WhatsApp summary, and CSV export.</p>
    </section>
    """


def _ai_pipeline_strip() -> str:
    """Return a compact visual pipeline for the app's AI and ledger flow."""
    stages = (
        ("Input", "Voice/Text"),
        ("Endpoint", "Modal Cloud"),
        ("Nemotron 4B", "NVIDIA Small LLM"),
        ("Extraction", "Strict JSON"),
        ("Fallback", "Rule Engine"),
        ("Database", "SQLite Edge"),
    )
    stage_markup = "".join(
        f"""
        <li>
          <strong>{escape(title)}</strong>
          <span>{escape(body)}</span>
        </li>
        """
        for title, body in stages
    )
    return f"""
    <section class="vl-pipeline-strip">
      <div>
        <h2>Small Model Intelligence</h2>
        <p>VoiceLedger leverages <strong>NVIDIA Nemotron-3-Nano-4B</strong> (Small but Mighty) via Modal, optimized for low-latency JSON extraction from messy multilingual notes.</p>
      </div>
      <ol>{stage_markup}</ol>
    </section>
    """


def _small_model_fit_card() -> str:
    """Return the small-model fit explanation for judges."""
    return """
    <section class="vl-small-model-card">
      <h2>Why Small Models Win Here</h2>
      <div>
        <span><strong>Speed & Latency</strong>Nemotron-3-Nano-4B returns structured data in &lt;500ms, essential for a busy seller in a "backyard" setting.</span>
        <span><strong>Constrained Context</strong>Bookkeeping notes are short. A 4B model is the "sweet spot" for high accuracy without the overhead of a 70B model.</span>
        <span><strong>Localization</strong>Smaller models are surprisingly good at handling Hinglish/multilingual shorthand when prompted with clear schemas.</span>
        <span><strong>Reliable Fallback</strong>If internet drops, our deterministic rule engine ensures the business never stops running.</span>
      </div>
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
        "field_test",
        "bulk",
        "credit",
        "inventory",
        "reports",
        "ledger",
    )
    return tuple(gr.update(visible=page_id == active_page) for page_id in page_ids)


def _reset_record_form() -> tuple[str, str, dict[str, Any], None, str, str, str, str, None, None, None, None, None, str, str, float]:
    """Clear the record flow for the next transaction."""
    return (
        "",
        "",
        _empty_transaction_payload(),
        None,
        "Ready for the next transaction.",
        _empty_review_card(),
        _empty_receipt_card(),
        *_empty_review_fields(),
    )


def _force_local_mode(ai_mode: str | None) -> bool:
    """Return whether the UI should skip Modal and use local fallbacks only."""
    return ai_mode == "Local fallback only"


def _ai_mode_status(ai_mode: str | None) -> str:
    """Render the current AI mode as a visible status card."""
    if _force_local_mode(ai_mode):
        return """
        <section class="vl-ai-mode-card vl-ai-mode-local">
          <h2>Local fallback only</h2>
          <p>VoiceLedger skips Modal and uses local faster-whisper/rule parsing. Useful for offline-style demos and reliability checks.</p>
        </section>
        """
    return """
    <section class="vl-ai-mode-card">
      <h2>Cloud AI first</h2>
      <p>The Space calls Modal first for speech and NVIDIA Nemotron parsing, then falls back locally if the cloud path is unavailable.</p>
    </section>
    """


def _currency_symbol_for_preset(preset: str | None) -> str:
    """Return the currency symbol for a selected preset."""
    return CURRENCY_PRESETS.get(preset or "Custom", "")


def _currency_preset_for_symbol(symbol: str | None) -> str:
    """Return a likely currency preset for an existing symbol."""
    cleaned = (symbol or "").strip()
    for preset, preset_symbol in CURRENCY_PRESETS.items():
        if preset != "Custom" and preset_symbol == cleaned:
            return preset
    return "Custom"


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


def _parse_note(
    note: str,
    db_path: str | Path | None = None,
    ai_mode: str = "Cloud AI first",
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    """Parse a note and return display data plus serializable state."""
    result = modal_api.parse_transaction_result(
        note,
        fallback=local_parse_transaction,
        force_local=_force_local_mode(ai_mode),
    )
    transaction = result.transaction
    transaction, price_memory_used = suggest_price_from_history(transaction, db_path)
    payload = transaction.model_dump()
    warnings = _review_warnings(transaction, db_path)
    if price_memory_used:
        warnings.append(PRICE_MEMORY_BADGE)
    status = _status_message(transaction, result.message, result.fallback_reason, warnings=warnings)
    return payload, payload, status, _review_card(transaction, result.message, warnings)


def _scan_receipt_for_editing(
    image_path: str | Path | None,
    db_path: str | Path | None,
    ai_mode: str = "Cloud AI first",
) -> tuple[dict[str, Any], dict[str, Any], str, str, str | None, float | None, float | None, float | None, str | None, str, str, float, str]:
    """Scan a receipt and return editable review fields."""
    if not image_path:
        return ({}, {}, "Please upload or take a photo of a receipt.", _empty_review_card(), *([None] * 5), "unknown", "unknown", 0.0, "")

    result = modal_api.scan_receipt_result(
        image_path,
        fallback=local_parse_transaction,
        force_local=_force_local_mode(ai_mode),
    )
    transaction = result.transaction
    transaction, price_memory_used = suggest_price_from_history(transaction, db_path)
    payload = transaction.model_dump()
    warnings = _review_warnings(transaction, db_path)
    if price_memory_used:
        warnings.append(PRICE_MEMORY_BADGE)
    
    status = _status_message(transaction, result.message, result.fallback_reason, warnings=warnings)
    review_card = _review_card(transaction, warnings=warnings)
    
    return (
        payload,
        payload,
        status,
        review_card,
        transaction.item,
        transaction.quantity,
        transaction.unit_price,
        transaction.amount,
        transaction.customer,
        transaction.transaction_type,
        transaction.payment_status,
        transaction.confidence,
        transaction.notes or "",
    )


def _parse_note_for_editing(
    note: str,
    db_path: str | Path | None = None,
    ai_mode: str = "Cloud AI first",
) -> tuple[dict[str, Any], dict[str, Any], str, str, str, str | None, float | None, float | None, float | None, str | None, str, str, float]:
    """Parse a note and populate editable review fields."""
    payload, state, status, review_card = _parse_note(note, db_path, ai_mode)
    return payload, state, status, review_card, *_payload_to_review_fields(payload)


def _transcribe_and_parse_audio(
    audio_path: Any,
    db_path: str | Path | None = None,
    ai_mode: str = "Cloud AI first",
) -> tuple[str, dict[str, Any], dict[str, Any] | None, str, str]:
    """Transcribe recorded audio, parse the transcript, and return UI updates."""
    force_local = _force_local_mode(ai_mode)
    try:
        transcription = modal_api.transcribe_audio_result(
            audio_path,
            fallback=local_transcribe_audio,
            force_local=force_local,
        )
    except Exception as exc:
        empty_payload = _empty_transaction_payload()
        return "", empty_payload, None, f"Transcription failed: {exc}", _empty_review_card()

    parse_result = modal_api.parse_transaction_result(
        transcription.transcript,
        fallback=local_parse_transaction,
        force_local=force_local,
    )
    transaction = parse_result.transaction
    transaction, price_memory_used = suggest_price_from_history(transaction, db_path)
    payload = transaction.model_dump()
    warnings = _review_warnings(transaction, db_path)
    if price_memory_used:
        warnings.append(PRICE_MEMORY_BADGE)
    status = _status_message(
        transaction,
        parse_result.message,
        parse_result.fallback_reason,
        prefix=_transcription_status(transcription),
        warnings=warnings,
    )
    return transcription.transcript, payload, payload, status, _review_card(transaction, parse_result.message, warnings)


def _transcribe_and_parse_audio_for_editing(
    audio_path: Any,
    db_path: str | Path | None = None,
    ai_mode: str = "Cloud AI first",
) -> tuple[str, dict[str, Any], dict[str, Any] | None, str, str, str, str | None, float | None, float | None, float | None, str | None, str, str, float]:
    """Transcribe and parse audio while populating editable review fields."""
    transcript, payload, state, status, review_card = _transcribe_and_parse_audio(audio_path, db_path, ai_mode)
    return transcript, payload, state, status, review_card, *_payload_to_review_fields(payload)


def _save_transaction(transaction_payload: dict[str, Any] | None, db_path: str | Path | None) -> str:
    """Save the parsed transaction payload to SQLite."""
    if not transaction_payload:
        return "Parse a transaction before saving."

    transaction = Transaction(**transaction_payload)
    transaction_id = add_transaction(transaction, db_path)
    return f"Saved transaction #{transaction_id}: {_transaction_summary(transaction)}."


def _apply_review_edits(
    transaction_payload: dict[str, Any] | None,
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
) -> tuple[dict[str, Any], dict[str, Any] | None, str, str]:
    """Apply inline review edits to parsed transaction state."""
    if not transaction_payload:
        empty_payload = _empty_transaction_payload()
        return empty_payload, None, "Parse a transaction before editing the review.", _empty_review_card()

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
    payload = transaction.model_dump()
    record_correction(transaction_payload, payload, db_path)
    warnings = _review_warnings(transaction, db_path)
    status = _status_message(transaction, "Review updated from your edits.", warnings=warnings)
    return payload, payload, status, _review_card(transaction, "Review updated from your edits.", warnings)


def _save_transaction_and_refresh(
    transaction_payload: dict[str, Any] | None,
    db_path: str | Path | None,
) -> tuple[str, str, str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler]:
    """Save a transaction and refresh the demo-critical data views."""
    if not transaction_payload:
        return ("Parse a transaction before saving.", _empty_receipt_card(), _command_center(db_path), *_refresh_core_views(db_path))

    transaction = Transaction(**transaction_payload)
    transaction_id = add_transaction(transaction, db_path)
    status = f"Saved transaction #{transaction_id}: {_transaction_summary(transaction)}."
    receipt = _receipt_card(transaction, transaction_id, db_path)
    return (status, receipt, _command_center(db_path), *_refresh_core_views(db_path))


def _save_reviewed_transaction_and_refresh(
    transaction_payload: dict[str, Any] | None,
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
    language: str = "English",
) -> tuple[str, str, str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler]:
    """Save edited review fields and refresh demo-critical data views."""
    if not transaction_payload:
        return ("Parse a transaction before saving.", _empty_receipt_card(), _command_center(db_path), *_refresh_core_views(db_path, language=language))

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
    transaction_id = add_transaction(transaction, db_path)
    status = f"Saved transaction #{transaction_id}: {_transaction_summary(transaction)}."
    receipt = _receipt_card(transaction, transaction_id, db_path)
    tts_msg = t("transaction_saved_tts", language)
    return (status, receipt, _command_center(db_path), *_refresh_core_views(db_path, language=language), tts_msg)


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
    language: str = "English",
) -> tuple[str, str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler, str]:
    """Update a transaction and refresh all dependent views."""
    parsed_id = _coerce_transaction_id(transaction_id)
    if parsed_id is None:
        return ("Enter a transaction id before updating.", _command_center(db_path), *_refresh_core_views(db_path, language=language), "")

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
        return (f"Could not update transaction: {exc}", _command_center(db_path), *_refresh_core_views(db_path, language=language), "")

    updated = update_transaction(parsed_id, transaction, db_path)
    if not updated:
        return (f"Transaction #{parsed_id} was not found.", _command_center(db_path), *_refresh_core_views(db_path, language=language), "")
    
    status = f"Updated transaction #{parsed_id}: {_transaction_summary(transaction)}."
    tts_msg = t("transaction_updated_tts", language)
    return (status, _command_center(db_path), *_refresh_core_views(db_path, language=language), tts_msg)


def _delete_transaction_and_refresh(
    transaction_id: float | int | None,
    db_path: str | Path | None,
    language: str = "English",
) -> tuple[str, str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler, str]:
    """Delete a transaction and refresh all dependent views."""
    parsed_id = _coerce_transaction_id(transaction_id)
    if parsed_id is None:
        return ("Enter a transaction id before deleting.", _command_center(db_path), *_refresh_core_views(db_path, language=language), "")

    deleted = delete_transaction(parsed_id, db_path)
    if not deleted:
        return (f"Transaction #{parsed_id} was not found.", _command_center(db_path), *_refresh_core_views(db_path, language=language), "")
    
    status = f"Deleted transaction #{parsed_id} and refreshed balances."
    tts_msg = t("transaction_deleted_tts", language)
    return (status, _command_center(db_path), *_refresh_core_views(db_path, language=language), tts_msg)


def _export_ledger_csv(db_path: str | Path | None) -> tuple[str, str]:
    """Export ledger transactions to CSV for Gradio download."""
    export_path = export_transactions_csv(db_path)
    return str(export_path), "Transactions CSV is ready."


def _seed_demo_transactions_and_refresh(
    db_path: str | Path | None,
    language: str = "English",
) -> tuple[str, str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler, str]:
    """Seed realistic demo transactions and refresh all dependent views."""
    saved_ids = [add_transaction(local_parse_transaction(note), db_path) for note in DEMO_NOTES]
    return (
        f"Seeded {len(saved_ids)} demo transactions. Last transaction id: #{saved_ids[-1]}.",
        _command_center(db_path),
        *_refresh_core_views(db_path, language=language),
        "",
    )


def _refresh_core_views(
    db_path: str | Path | None,
    language: str = "English",
) -> tuple[str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, pd.DataFrame, pd.io.formats.style.Styler]:
    """Return dashboard, ledger, customer, and inventory refresh values."""
    return (
        *_get_dashboard_data(db_path, language=language),
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


def _save_seller_setup_and_refresh(
    business_name: str,
    currency_symbol: str,
    low_stock_threshold: float | None,
    language_style: str,
    db_path: str | Path | None,
) -> tuple[str, str, str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, pd.io.formats.style.Styler]:
    """Save seller setup and refresh context-sensitive dashboard views."""
    settings = update_business_settings(
        business_name=business_name,
        currency_symbol=currency_symbol,
        low_stock_threshold=low_stock_threshold,
        language_style=language_style,
        db_path=db_path,
    )
    return (
        _seller_setup_status(settings),
        _command_center(db_path),
        *_get_dashboard_data(db_path),
        _get_inventory_display(db_path),
    )


def _save_field_notes(
    who: str,
    tried: str,
    changed: str,
    db_path: str | Path | None,
    *,
    pain_point: str | None = None,
    before: str | None = None,
    after: str | None = None,
    useful: str | None = None,
) -> str:
    """Persist anonymized field-test notes."""
    update_business_settings(
        db_path=db_path,
        field_test_who=who,
        field_test_tried=tried,
        field_test_changed=changed,
        field_pain_point=pain_point,
        field_before=before,
        field_after=after,
        field_useful_moments=useful,
    )
    return "Saved anonymized field-test notes."


def _save_field_test_evidence(
    checklist: list[str] | None,
    who: str,
    tried: str,
    changed: str,
    db_path: str | Path | None,
    *,
    pain_point: str | None = None,
    before: str | None = None,
    after: str | None = None,
    useful: str | None = None,
    changed_after_feedback: str | None = None,
) -> str:
    """Persist field-test checklist and notes."""
    checklist_value = ",".join(checklist or [])
    settings = update_business_settings(
        db_path=db_path,
        field_test_who=who,
        field_test_tried=tried,
        field_test_changed=changed,
        field_test_checklist=checklist_value,
        field_pain_point=pain_point,
        field_before=before,
        field_after=after,
        field_useful_moments=useful,
        field_changed_after_feedback=changed_after_feedback,
    )
    return _field_test_summary(settings)


def _field_test_checklist_values(settings: dict[str, str]) -> list[str]:
    """Return stored field-test checklist selections."""
    raw_value = settings.get("field_test_checklist", "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _field_test_summary(settings: dict[str, str]) -> str:
    """Return a concise field-test evidence summary."""
    completed = _field_test_checklist_values(settings)
    return (
        f"Field test evidence saved: {len(completed)} checklist item(s). "
        f"Who: {settings['field_test_who']} Pain point: {settings['field_pain_point']} "
        f"Changed: {settings['field_changed_after_feedback']}"
    )


def _get_dashboard_data(
    db_path: str | Path | None,
    language: str = "English",
) -> tuple[str, str, str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, str, str]:
    """Return business insight values for the Dashboard section."""
    settings = get_business_settings(db_path)
    currency_symbol = settings["currency_symbol"]
    threshold = get_low_stock_threshold(db_path)
    sales = calculate_daily_sales(db_path)
    expenses = calculate_daily_expenses(db_path)
    profit = calculate_net_profit(db_path)
    credit = outstanding_credit(db_path)
    top_items = top_selling_items(db_path)
    low_stock = low_stock_items(db_path, threshold=threshold)
    timeline = _daily_timeline(db_path)
    seller_day = _seller_day_timeline(db_path)
    top_item = "No sales recorded today"
    if not top_items.empty:
        first_item = top_items.iloc[0]
        top_item = f"{first_item['item']} ({_format_quantity(first_item['quantity_sold'])} sold)"

    return (
        _metric_card("Total Sales Today", _format_money(sales, currency_symbol), "Recorded sales"),
        _metric_card("Total Expenses Today", _format_money(expenses, currency_symbol), "Purchases and costs"),
        _metric_card("Net Profit", _format_money(profit, currency_symbol), "Sales minus expenses", profit=profit),
        _metric_card("Outstanding Credit", _format_money(credit, currency_symbol), "Customer dues"),
        top_item,
        timeline,
        top_items,
        low_stock,
        _insight_coach(db_path, language=language),
        seller_day,
    )


def _insight_coach(db_path: str | Path | None, language: str = "English") -> str:
    """Return practical next-step coaching from today's ledger state."""
    settings = get_business_settings(db_path)
    currency = settings["currency_symbol"]
    threshold = get_low_stock_threshold(db_path)
    ledger = get_transactions(db_path)
    sales = calculate_daily_sales(db_path)
    expenses = calculate_daily_expenses(db_path)
    profit = calculate_net_profit(db_path)
    credit = outstanding_credit(db_path)
    top_items = top_selling_items(db_path)
    low_stock = low_stock_items(db_path, threshold=threshold)
    customer_balances = get_customer_balances(db_path)

    # 1. Deterministic Rule-Based Insights (Basic translations for demo)
    insights: list[tuple[str, str, str]] = []
    if ledger.empty:
        insights.append(("Start", "Record first transaction", "Use voice or text to add a sale, expense, credit, payment, or stock purchase."))
    if sales == 0 and not ledger.empty:
        insights.append(("Sales", "No sales yet today", "Focus on recording your first sale to track today's profit."))
    if expenses > sales and expenses > 0:
        insights.append(("Profit", "Expenses are above sales", f"Profit is {currency}{profit} today. Review costs before daily closeout."))
    if credit > 0 and not customer_balances.empty:
        balances = customer_balances.copy()
        balances["outstanding_balance"] = pd.to_numeric(balances["outstanding_balance"], errors="coerce").fillna(0)
        balances = balances.sort_values("outstanding_balance", ascending=False)
        customer = str(balances.iloc[0]["customer"])
        balance = float(balances.iloc[0]["outstanding_balance"])
        insights.append(("Credit", f"Follow up with {customer}", f"{customer} has {currency}{balance} outstanding. Use Customer Follow-up to generate a message."))
    if not low_stock.empty:
        item = str(low_stock.iloc[0]["item"])
        stock = float(low_stock.iloc[0]["current_stock"])
        insights.append(("Stock", f"Restock {item}", f"Current stock is {stock}, below the threshold of {threshold}."))
    if not top_items.empty:
        item = str(top_items.iloc[0]["item"])
        quantity = top_items.iloc[0]["quantity_sold"]
        insights.append(("Demand", f"Top product: {item}", f"{quantity} sold today. Keep this item visible and stocked."))

    # 2. LLM-Generated Strategic Insights
    llm_insights_html = ""
    if not ledger.empty:
        summary = get_business_summary(db_path)
        # We can ask the LLM to provide advice in the target language!
        prompt_language = language if language != "Hindi" else "Hindi (using Devanagari script)"
        llm_advice = generate_business_insights(f"{summary}\n\nPlease provide the advice in {prompt_language}.")
        
        # Format markdown-style bullet points into HTML
        advice_items = [line.strip("- ").strip() for line in llm_advice.split("\n") if line.strip().startswith("-") or line.strip()[:1].isdigit()]
        if not advice_items:
             advice_items = [line.strip() for line in llm_advice.split(". ") if len(line) > 10][:3]
        
        advice_rows = "".join(f"<li>{escape(item)}</li>" for item in advice_items)
        ai_coach_label = "AI Business Coach" if language == "English" else f"AI Business Coach ({language})"
        if language == "Spanish": ai_coach_label = "Entrenador de Negocios IA"
        if language == "Hindi": ai_coach_label = "AI बिजनेस कोच"
        
        llm_insights_html = f"""
        <div class="vl-llm-insights">
          <h3>{ai_coach_label}</h3>
          <ul>{advice_rows}</ul>
        </div>
        """

    rows = "".join(
        f"""
        <li>
          <span>{escape(label)}</span>
          <strong>{escape(title)}</strong>
          <p>{escape(body)}</p>
        </li>
        """
        for label, title, body in insights[:4]
    )
    return f"""
    <section class="vl-insight-coach">
      <h2>{t("insight_coach_title", language)}</h2>
      <p>{t("insight_coach_subtitle", language)}</p>
      <ol>{rows}</ol>
      {llm_insights_html}
    </section>
    """


def _command_center(db_path: str | Path | None) -> str:
    """Return the top-of-record-page seller command center."""
    settings = get_business_settings(db_path)
    currency = settings["currency_symbol"]
    threshold = get_low_stock_threshold(db_path)
    sales = calculate_daily_sales(db_path)
    credit = outstanding_credit(db_path)
    low_stock_count = len(low_stock_items(db_path, threshold=threshold))
    last_transaction = _last_transaction_label(db_path)
    return f"""
    <section class="vl-command-center">
      <h2>{escape(settings['business_name'])} Command Center</h2>
      <div>
        <span><strong>Sales today</strong>{escape(_format_money(sales, currency))}</span>
        <span><strong>Outstanding credit</strong>{escape(_format_money(credit, currency))}</span>
        <span><strong>Low-stock items</strong>{low_stock_count}</span>
        <span><strong>Last saved</strong>{escape(last_transaction)}</span>
      </div>
    </section>
    """


def _seller_setup_status(settings: dict[str, str]) -> str:
    """Return a concise seller setup status line."""
    return (
        f"Seller setup: {settings['business_name']} · currency {settings['currency_symbol']} · "
        f"low stock below {settings['low_stock_threshold']} · {settings['language_style']}."
    )


def suggest_price_from_history(transaction: Transaction, db_path: str | Path | None) -> tuple[Transaction, bool]:
    """Fill missing sale price fields from the latest saved sale for the same item."""
    if (
        transaction.transaction_type != "sale"
        or not transaction.item
        or transaction.quantity is None
        or transaction.unit_price is not None
        or transaction.amount is not None
    ):
        return transaction, False

    ledger = get_transactions(db_path)
    if ledger.empty:
        return transaction, False

    item_name = transaction.item.lower()
    matches = ledger[
        (ledger["transaction_type"] == "sale")
        & (ledger["item"].fillna("").astype(str).str.lower() == item_name)
    ].copy()
    if matches.empty:
        return transaction, False

    matches["unit_price"] = pd.to_numeric(matches["unit_price"], errors="coerce")
    matches = matches[matches["unit_price"].notna() & (matches["unit_price"] > 0)]
    if matches.empty:
        return transaction, False

    unit_price = float(matches.iloc[0]["unit_price"])
    payload = transaction.model_dump()
    payload["unit_price"] = unit_price
    payload["amount"] = round(float(transaction.quantity) * unit_price, 2)
    payload["confidence"] = max(float(transaction.confidence), 0.78)
    return Transaction(**payload), True


def get_debt_reminder_queue(db_path: str | Path | None = None) -> pd.DataFrame:
    """Return customers with positive outstanding balances sorted by balance."""
    balances = get_customer_balances(db_path)
    columns = ["customer", "outstanding_balance", "suggested_message"]
    if balances.empty:
        return pd.DataFrame(columns=columns)

    debt = balances.copy()
    debt["outstanding_balance"] = pd.to_numeric(debt["outstanding_balance"], errors="coerce").fillna(0)
    debt = debt[debt["outstanding_balance"] > 0].sort_values("outstanding_balance", ascending=False)
    if debt.empty:
        return pd.DataFrame(columns=columns)

    debt["suggested_message"] = debt["customer"].apply(lambda customer: generate_debt_reminder(str(customer), db_path))
    return debt[columns].reset_index(drop=True)


def generate_debt_reminder(customer_name: str, db_path: str | Path | None = None) -> str:
    """Generate a WhatsApp-ready reminder for one customer's outstanding balance."""
    return generate_customer_followup(customer_name, db_path)


def generate_reorder_intelligence(db_path: str | Path | None = None) -> pd.DataFrame:
    """Return stock recommendations with sales velocity context."""
    columns = ["item", "current_stock", "recent_sold", "threshold", "status", "suggested_action"]
    inventory = get_inventory(db_path)
    if inventory.empty:
        return pd.DataFrame(columns=columns)

    threshold = get_low_stock_threshold(db_path)
    ledger = get_transactions(db_path)
    stock = inventory.copy()
    stock["current_stock"] = pd.to_numeric(stock["current_stock"], errors="coerce").fillna(0)
    sales_by_item: dict[str, float] = {}
    if not ledger.empty:
        sale_rows = ledger[ledger["transaction_type"] == "sale"].copy()
        sale_rows["quantity"] = pd.to_numeric(sale_rows["quantity"], errors="coerce").fillna(0)
        sale_rows["item_key"] = sale_rows["item"].fillna("").astype(str).str.lower()
        sales_by_item = sale_rows.groupby("item_key")["quantity"].sum().to_dict()

    records: list[dict[str, Any]] = []
    for _, row in stock.iterrows():
        item = str(row["item"])
        current_stock = float(row["current_stock"])
        recent_sold = float(sales_by_item.get(item.lower(), 0.0))
        status = "Stock ok"
        if current_stock < threshold:
            status = "Low stock"
        elif recent_sold > 0 and current_stock <= max(threshold * 2, recent_sold):
            status = "Selling fast"
        if status == "Low stock":
            action = f"Restock {item} now; stock is below {_format_quantity(threshold)}."
        elif status == "Selling fast":
            action = f"Plan {item} restock soon; recent sales are {_format_quantity(recent_sold)}."
        else:
            action = f"{item} stock is ok."
        records.append(
            {
                "item": item,
                "current_stock": current_stock,
                "recent_sold": recent_sold,
                "threshold": threshold,
                "status": status,
                "suggested_action": action,
            }
        )

    recommendations = pd.DataFrame.from_records(records, columns=columns)
    recommendations["_status_rank"] = recommendations["status"].map({"Low stock": 0, "Selling fast": 1, "Stock ok": 2})
    return recommendations.sort_values(["_status_rank", "current_stock", "item"]).drop(columns=["_status_rank"]).reset_index(drop=True)


def get_guided_demo_status(db_path: str | Path | None = None) -> str:
    """Return compact progress states for the judge demo flow."""
    ledger = get_transactions(db_path)
    has_transactions = not ledger.empty
    has_sale = has_transactions and bool((ledger["transaction_type"] == "sale").any())
    has_closeout_exports = Path(tempfile.gettempdir(), "voiceledger_transactions.csv").exists()
    health_ready = initialize_database(db_path).exists()
    steps = [
        ("Check Health", health_ready, "Demo Health is reachable from this page."),
        ("Seed Demo Data", has_transactions, "Adds realistic sales, expenses, credit, and stock."),
        ("Record/Type Sale", has_sale, "Try Sold 12 mangoes, 20 each."),
        ("Save", has_transactions, "Receipt, ledger, dashboard, credit, and stock refresh."),
        ("Open Dashboard", has_transactions, "Metrics and timeline are ready once data exists."),
        ("Open Reports", has_closeout_exports, "Daily Closeout prepares PDF, WhatsApp, and CSV."),
    ]
    items = "".join(
        f"""
        <li class="{'vl-guided-done' if done else 'vl-guided-next'}">
          <strong>{escape(label)}</strong>
          <span>{'Done' if done else 'Next'} · {escape(help_text)}</span>
        </li>
        """
        for label, done, help_text in steps
    )
    return f"""
    <section class="vl-guided-mode">
      <h2>Guided Judge Mode</h2>
      <p>Use this path for a 90-second demo: health, seed, record, save, dashboard, reports.</p>
      <ol>{items}</ol>
    </section>
    """


def _last_transaction_label(db_path: str | Path | None) -> str:
    """Return a concise label for the newest transaction."""
    ledger = get_transactions(db_path)
    if ledger.empty:
        return "None yet"
    row = ledger.iloc[0]
    amount = row.get("amount")
    item_or_customer = row.get("item") or row.get("customer") or "transaction"
    if pd.notna(amount):
        return f"{row['transaction_type']} · {item_or_customer} · {_format_money(float(amount), get_business_settings(db_path)['currency_symbol'])}"
    return f"{row['transaction_type']} · {item_or_customer}"


def _seller_day_timeline(db_path: str | Path | None) -> str:
    """Return a visual timeline of recent seller activity."""
    ledger = get_transactions(db_path)
    if ledger.empty:
        return _empty_detail_card("Seller day timeline", "No saved transactions yet.")

    rows = []
    currency = get_business_settings(db_path)["currency_symbol"]
    for _, row in ledger.head(8).iterrows():
        label = _transaction_type_label(str(row["transaction_type"]))
        subject = row.get("item") or row.get("customer") or "ledger entry"
        amount = row.get("amount")
        amount_text = ""
        if pd.notna(amount):
            amount_text = f" · {_format_money(float(amount), currency)}"
        rows.append(
            f"""
            <li>
              <strong>{escape(label)}</strong>
              <span>{escape(str(subject))}{escape(amount_text)}</span>
            </li>
            """
        )
    return f"""
    <section class="vl-seller-timeline">
      <h2>Seller day timeline</h2>
      <ol>{''.join(rows)}</ol>
    </section>
    """


def _transaction_type_label(transaction_type: str) -> str:
    """Return a compact human label for a transaction type."""
    return {
        "sale": "Sale",
        "expense": "Expense",
        "inventory_purchase": "Stock purchase",
        "customer_credit": "Customer owes",
        "customer_payment": "Customer paid",
    }.get(transaction_type, "Needs review")


def _daily_timeline(db_path: str | Path | None) -> pd.DataFrame:
    """Return chart-ready daily sales and expense rows."""
    transactions = get_transactions(db_path)
    columns = ["date", "kind", "amount"]
    if transactions.empty or "created_at" not in transactions:
        return pd.DataFrame(columns=columns)

    data = transactions.copy()
    data["date"] = pd.to_datetime(data["created_at"], errors="coerce").dt.strftime("%Y-%m-%d")
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce").fillna(0)
    data["kind"] = data["transaction_type"].map(
        {
            "sale": "Sales",
            "expense": "Expenses",
            "inventory_purchase": "Expenses",
        }
    )
    data = data[data["kind"].notna() & data["date"].notna()]
    if data.empty:
        return pd.DataFrame(columns=columns)

    grouped = data.groupby(["date", "kind"], as_index=False)["amount"].sum()
    return grouped.sort_values(["date", "kind"]).reset_index(drop=True)


def _get_inventory_display(db_path: str | Path | None) -> pd.io.formats.style.Styler:
    """Return inventory with low-stock rows highlighted for Gradio display."""
    inventory = get_inventory(db_path)
    threshold = get_low_stock_threshold(db_path)
    return inventory.style.apply(lambda row: _highlight_low_stock(row, threshold), axis=1)


def _get_customer_detail(customer_name: str | None, db_path: str | Path | None) -> tuple[str, pd.DataFrame]:
    """Return customer balance summary and transaction history."""
    name = (customer_name or "").strip()
    columns = ["id", "transaction_type", "amount", "notes", "created_at"]
    if not name:
        return _empty_detail_card("Customer detail", "Enter a customer name."), pd.DataFrame(columns=columns)

    ledger = get_transactions(db_path)
    if ledger.empty:
        return _empty_detail_card("Customer detail", "No saved transactions yet."), pd.DataFrame(columns=columns)

    matches = ledger[ledger["customer"].fillna("").str.lower() == name.lower()].copy()
    if matches.empty:
        return _empty_detail_card("Customer detail", f"No transactions found for {name}."), pd.DataFrame(columns=columns)

    credit = pd.to_numeric(matches.loc[matches["transaction_type"] == "customer_credit", "amount"], errors="coerce").fillna(0).sum()
    paid = pd.to_numeric(matches.loc[matches["transaction_type"] == "customer_payment", "amount"], errors="coerce").fillna(0).sum()
    balance = round(float(credit - paid), 2)
    status = "clear"
    if balance > 0:
        status = "owes"
    elif balance < 0:
        status = "overpaid"
    currency = get_business_settings(db_path)["currency_symbol"]
    summary = f"""
    <section class="vl-detail-card">
      <h2>{escape(name)} · {status}</h2>
      <p>Outstanding balance: <strong>{_format_money(balance, currency)}</strong>. Credit: {_format_money(float(credit), currency)}. Payments: {_format_money(float(paid), currency)}.</p>
    </section>
    """
    return summary, matches[columns].reset_index(drop=True)


def _get_inventory_detail(item: str | None, db_path: str | Path | None) -> tuple[str, pd.DataFrame]:
    """Return inventory summary and item movement history."""
    item_name = (item or "").strip().lower()
    columns = ["id", "transaction_type", "quantity", "amount", "notes", "created_at"]
    if not item_name:
        return _empty_detail_card("Inventory detail", "Enter an item name."), pd.DataFrame(columns=columns)

    ledger = get_transactions(db_path)
    if ledger.empty:
        return _empty_detail_card("Inventory detail", "No saved transactions yet."), pd.DataFrame(columns=columns)

    matches = ledger[ledger["item"].fillna("").str.lower() == item_name].copy()
    if matches.empty:
        return _empty_detail_card("Inventory detail", f"No movement found for {item_name}."), pd.DataFrame(columns=columns)

    bought = pd.to_numeric(matches.loc[matches["transaction_type"] == "inventory_purchase", "quantity"], errors="coerce").fillna(0).sum()
    sold = pd.to_numeric(matches.loc[matches["transaction_type"] == "sale", "quantity"], errors="coerce").fillna(0).sum()
    stock = round(float(bought - sold), 2)
    threshold = get_low_stock_threshold(db_path)
    status = "low stock" if stock < threshold else "in stock"
    summary = f"""
    <section class="vl-detail-card">
      <h2>{escape(item_name)} · {status}</h2>
      <p>Bought: {_format_quantity(bought)}. Sold: {_format_quantity(sold)}. Current stock: <strong>{_format_quantity(stock)}</strong>. Low-stock threshold: {_format_quantity(threshold)}.</p>
    </section>
    """
    return summary, matches[columns].reset_index(drop=True)


def _run_voice_command(command: str | None, db_path: str | Path | None) -> str:
    """Run a lightweight text/voice command shortcut."""
    cleaned = " ".join(str(command or "").split()).strip()
    if not cleaned:
        return _empty_detail_card("Command result", "Try close today, show Amit, or stock mangoes.")

    lowered = cleaned.lower()
    if lowered in {"close today", "daily closeout", "closeout", "summary"}:
        summary, pdf_path, csv_path, whatsapp, status = _run_daily_closeout(db_path)
        file_note = f"PDF: {pdf_path or 'needs attention'}. CSV: {csv_path or 'needs attention'}."
        return f"{summary}<section class=\"vl-detail-card\"><h2>Command result</h2><p>{escape(status)} {escape(file_note)}</p><pre>{escape(whatsapp)}</pre></section>"

    if lowered.startswith(("show ", "customer ")):
        customer = cleaned.split(" ", 1)[1] if " " in cleaned else ""
        summary, _ = _get_customer_detail(customer, db_path)
        return summary

    if lowered.startswith(("stock ", "inventory ")):
        item = cleaned.split(" ", 1)[1] if " " in cleaned else ""
        summary, _ = _get_inventory_detail(item, db_path)
        return summary

    parsed = local_parse_transaction(cleaned)
    if parsed.transaction_type != "unknown":
        warnings = _review_warnings(parsed, db_path)
        return _review_card(parsed, "Command parsed as a transaction. Copy it into the transaction note to save.", warnings)

    return _empty_detail_card("Command result", "Command not recognized. Try close today, show Amit, stock mangoes, or a transaction note.")


def _generate_reorder_intelligence_for_ui(db_path: str | Path | None) -> tuple[pd.DataFrame, str]:
    """Return reorder intelligence and a WhatsApp-ready restock message."""
    recommendations = generate_reorder_intelligence(db_path)
    if recommendations.empty:
        return recommendations, "No inventory recorded yet."

    settings = get_business_settings(db_path)
    message_lines = [
        f"{settings['business_name']} Reorder Plan",
        f"Low-stock threshold: {_format_quantity(get_low_stock_threshold(db_path))}",
        "",
    ]
    action_rows = recommendations[recommendations["status"].isin(["Low stock", "Selling fast"])]
    if action_rows.empty:
        message_lines.append("All stock looks ok today.")
    else:
        message_lines.extend(
            f"- {row['item'].title()}: {row['status']} ({_format_quantity(row['current_stock'])} left, {_format_quantity(row['recent_sold'])} sold recently)"
            for _, row in action_rows.head(8).iterrows()
        )
    return recommendations, "\n".join(message_lines)


def _generate_daily_summary_report(db_path: str | Path | None) -> tuple[str | None, str]:
    """Generate the Daily Summary PDF for download in Gradio."""
    settings = get_business_settings(db_path)
    try:
        report_path = generate_daily_summary_pdf(
            db_path=db_path,
            business_name=settings["business_name"],
            currency_symbol=settings["currency_symbol"],
        )
    except Exception as exc:
        return None, f"Could not generate report: {exc}"
    return str(report_path), "Daily Summary PDF is ready."


def _run_daily_closeout(db_path: str | Path | None) -> tuple[str, str | None, str | None, str, str]:
    """Generate the daily closeout summary and exports."""
    settings = get_business_settings(db_path)
    currency = settings["currency_symbol"]
    threshold = get_low_stock_threshold(db_path)
    sales = calculate_daily_sales(db_path)
    expenses = calculate_daily_expenses(db_path)
    profit = calculate_net_profit(db_path)
    credit = outstanding_credit(db_path)
    low_stock = low_stock_items(db_path, threshold=threshold)

    pdf_path: str | None
    csv_path: str | None
    try:
        pdf_path = str(
            generate_daily_summary_pdf(
                db_path=db_path,
                business_name=settings["business_name"],
                currency_symbol=currency,
            )
        )
    except Exception:
        pdf_path = None
    try:
        csv_path = str(export_transactions_csv(db_path))
    except Exception:
        csv_path = None

    whatsapp = generate_whatsapp_summary(
        db_path=db_path,
        low_stock_threshold=threshold,
        business_name=settings["business_name"],
        currency_symbol=currency,
    )
    summary = f"""
    <section class="vl-closeout-card">
      <h2>Daily Closeout Ready</h2>
      <div class="vl-closeout-grid">
        <span><strong>Sales</strong>{_format_money(sales, currency)}</span>
        <span><strong>Expenses</strong>{_format_money(expenses, currency)}</span>
        <span><strong>Profit</strong>{_format_money(profit, currency)}</span>
        <span><strong>Credit</strong>{_format_money(credit, currency)}</span>
      </div>
      <p>{len(low_stock)} low-stock item(s). PDF, WhatsApp summary, and CSV are prepared below.</p>
    </section>
    """
    status = "Daily closeout complete."
    if pdf_path is None:
        status += " PDF generation needs attention."
    if csv_path is None:
        status += " CSV export needs attention."
    return summary, pdf_path, csv_path, whatsapp, status


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
    """Render a dashboard metric card with icons."""
    tone = ""
    icon = "📊"
    if "Sales" in label: icon = "💰"
    if "Expenses" in label: icon = "💸"
    if "Profit" in label: icon = "📈" if (profit or 0) >= 0 else "📉"
    if "Credit" in label: icon = "🤝"
    
    if profit is not None:
        tone = " vl-profit-positive" if profit >= 0 else " vl-profit-negative"
    return f"""
    <div class="vl-metric-card{tone}">
      <div class="vl-metric-icon">{icon}</div>
      <div class="vl-metric-content">
        <div class="vl-metric-label">{label}</div>
        <div class="vl-metric-value">{value}</div>
        <div class="vl-metric-note">{note}</div>
      </div>
    </div>
    """


def _generate_whatsapp_summary(db_path: str | Path | None, language: str = "English") -> str:
    """Generate a WhatsApp summary using seller settings."""
    settings = get_business_settings(db_path)
    return generate_whatsapp_summary(
        db_path=db_path,
        low_stock_threshold=get_low_stock_threshold(db_path),
        business_name=settings["business_name"],
        currency_symbol=settings["currency_symbol"],
        language=language,
    )


def _format_money(value: float, currency_symbol: str | None = None) -> str:
    """Format money for dashboard cards."""
    symbol = currency_symbol if currency_symbol is not None else get_business_settings()["currency_symbol"]
    amount = float(value)
    if amount.is_integer():
        return f"{symbol}{int(amount):,}"
    return f"{symbol}{amount:,.2f}"


def _highlight_low_stock(row: pd.Series, threshold: float = LOW_STOCK_THRESHOLD) -> list[str]:
    """Highlight rows where stock is below the configured threshold."""
    current_stock = row.get("current_stock")
    if current_stock is not None and float(current_stock) < threshold:
        return ["background-color: #fff3cd; color: #5f370e"] * len(row)
    return [""] * len(row)


def _format_quantity(value: object) -> str:
    """Format quantity values for concise dashboard text."""
    quantity = float(value)
    if quantity.is_integer():
        return str(int(quantity))
    return f"{quantity:.2f}"


def _format_optional_number(value: object) -> str:
    """Format optional numeric fields for review cards."""
    if value is None:
        return "—"
    return _format_quantity(value)


def _empty_transaction_payload() -> dict[str, Any]:
    """Return a serializable empty transaction for UI display."""
    return Transaction().model_dump()


def _empty_review_fields() -> tuple[str, None, None, None, None, None, str, str, float]:
    """Return default values for editable review fields."""
    return "unknown", None, None, None, None, None, "unknown", "", 0.0


def _payload_to_review_fields(payload: dict[str, Any] | None) -> tuple[str, str | None, float | None, float | None, float | None, str | None, str, str, float]:
    """Convert a transaction payload into editable review field values."""
    if not payload:
        return _empty_review_fields()
    transaction = Transaction(**payload)
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
    )


def _empty_review_card() -> str:
    """Return the initial review card markup."""
    return _empty_detail_card("Transaction review", "Parse a note to review fields, confidence, and warnings.")


def _empty_receipt_card() -> str:
    """Return the initial save receipt markup."""
    return _empty_detail_card("Saved just now", "Save a reviewed transaction to see the receipt.")


def _empty_detail_card(title: str, body: str = "Select an item to see details.") -> str:
    """Return a neutral detail card."""
    return f"""
    <section class="vl-detail-card">
      <h2>{escape(title)}</h2>
      <p>{escape(body)}</p>
    </section>
    """


def _review_card(transaction: Transaction, source_message: str, warnings: list[str]) -> str:
    """Render a human-friendly transaction review card."""
    readiness = _review_readiness(transaction, warnings)
    warning_markup = "".join(
        f'<span class="{_warning_badge_class(warning)}">{escape(warning)}</span>'
        for warning in warnings
    )
    warning_markup = f"{readiness}{warning_markup}"

    fields = [
        ("Type", transaction.transaction_type),
        ("Item", transaction.item or "—"),
        ("Quantity", _format_optional_number(transaction.quantity)),
        ("Unit price", _format_money(transaction.unit_price) if transaction.unit_price is not None else "—"),
        ("Amount", _format_money(transaction.amount) if transaction.amount is not None else "—"),
        ("Customer", transaction.customer or "—"),
        ("Confidence", f"{transaction.confidence:.2f}"),
    ]
    field_markup = "".join(
        f"<div><span>{escape(label)}</span><strong>{escape(str(value))}</strong></div>"
        for label, value in fields
    )
    return f"""
    <section class="vl-review-card">
      <div class="vl-review-header">
        <h2>Review transaction</h2>
        <p>{escape(source_message)}</p>
      </div>
      <div class="vl-review-grid">{field_markup}</div>
      <div class="vl-warning-row">{warning_markup}</div>
    </section>
    """


def _review_warnings(transaction: Transaction, db_path: str | Path | None) -> list[str]:
    """Return smart review warnings before saving."""
    warnings: list[str] = []
    if transaction.transaction_type == "unknown":
        warnings.append("Unknown type")
    if transaction.transaction_type in {"sale", "inventory_purchase"} and not transaction.item:
        warnings.append("Missing item")
    if transaction.amount is None and transaction.transaction_type in {"sale", "expense", "customer_credit", "customer_payment"}:
        warnings.append("Missing amount")
    if transaction.transaction_type in {"customer_credit", "customer_payment"} and not transaction.customer:
        warnings.append("Missing customer")
    if transaction.confidence < 0.75:
        warnings.append("Low confidence")
    if _would_make_stock_negative(transaction, db_path):
        warnings.append("Inventory would go negative")
    if _is_duplicate_transaction(transaction, db_path):
        warnings.append("Possible duplicate")
    return warnings


def _review_readiness(transaction: Transaction, warnings: list[str]) -> str:
    """Return the primary trust cue for a parsed transaction."""
    blocking_warnings = {"Unknown type", "Missing item", "Missing amount", "Missing customer", "Inventory would go negative"}
    if transaction.transaction_type == "inventory_purchase" and transaction.quantity is not None:
        blocking_warnings.discard("Missing amount")
    if any(warning in blocking_warnings for warning in warnings):
        return '<span class="vl-warning-badge vl-warning-strong">Needs review</span>'
    return '<span class="vl-success-badge">Safe to save</span>'


def _warning_badge_class(warning: str) -> str:
    """Return a severity-aware warning badge class."""
    if warning == PRICE_MEMORY_BADGE:
        return "vl-success-badge"
    if warning in {"Inventory would go negative", "Possible duplicate"}:
        return "vl-warning-badge vl-warning-strong"
    return "vl-warning-badge"


def _would_make_stock_negative(transaction: Transaction, db_path: str | Path | None) -> bool:
    """Return whether saving this sale would take inventory below zero."""
    if transaction.transaction_type != "sale" or not transaction.item or transaction.quantity is None:
        return False
    inventory = get_inventory(db_path)
    if inventory.empty:
        return transaction.quantity > 0
    matches = inventory[inventory["item"].astype(str).str.lower() == transaction.item.lower()]
    if matches.empty:
        return transaction.quantity > 0
    current_stock = float(matches.iloc[0]["current_stock"])
    return current_stock - float(transaction.quantity) < 0


def _is_duplicate_transaction(transaction: Transaction, db_path: str | Path | None) -> bool:
    """Return whether a similar transaction exists in the last five minutes."""
    ledger = get_transactions(db_path)
    if ledger.empty or "created_at" not in ledger:
        return False
    created_at = pd.to_datetime(ledger["created_at"], errors="coerce")
    recent = ledger[created_at >= datetime.now() - timedelta(minutes=5)].copy()
    if recent.empty:
        return False
    comparable = recent[
        (recent["transaction_type"] == transaction.transaction_type)
        & (recent["item"].fillna("").str.lower() == (transaction.item or "").lower())
        & (recent["customer"].fillna("").str.lower() == (transaction.customer or "").lower())
    ]
    if transaction.amount is not None and not comparable.empty:
        amounts = pd.to_numeric(comparable["amount"], errors="coerce").fillna(-1)
        comparable = comparable[amounts == float(transaction.amount)]
    return not comparable.empty


import qrcode
from io import BytesIO
import base64
from PIL import Image

def _generate_qr_code(data: str) -> str:
    """Generate a base64 encoded QR code image."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def _payment_qr_panel(transaction: Transaction, settings: dict[str, str]) -> str:
    """Return a QR code panel for payments if applicable."""
    if transaction.transaction_type != "sale" or transaction.payment_status == "paid":
        return ""
    
    # Mocking a UPI/Payment URI for the demo
    # In a real app, this would use settings['payment_id']
    business = settings.get("business_name", "VoiceLedger Seller")
    amount = transaction.amount or 0
    payment_uri = f"upi://pay?pa=seller@bank&pn={business}&am={amount}&cu=INR"
    qr_base64 = _generate_qr_code(payment_uri)
    
    return f"""
    <div class="vl-qr-panel">
      <h3>{t("qr_payment_title", settings.get("language", "English"))}</h3>
      <p>{t("qr_payment_subtitle", settings.get("language", "English"))}</p>
      <img src="{qr_base64}" alt="Payment QR Code" style="width: 200px; height: 200px; margin: 10px auto; display: block;" />
      <p style="text-align: center; font-weight: bold;">Amount: {settings.get("currency_symbol", "₹")}{amount}</p>
    </div>
    """

def _receipt_card(transaction: Transaction, transaction_id: int, db_path: str | Path | None) -> str:
    """Render a post-save receipt card."""
    summary = _transaction_summary(transaction)
    side_effect = _side_effect_summary(transaction, db_path)
    settings = get_business_settings(db_path)
    qr_panel = _payment_qr_panel(transaction, settings)
    
    return f"""
    <section class="vl-receipt-card">
      <h2>Saved just now</h2>
      <p>Transaction #{transaction_id}: {escape(summary)}.</p>
      <p>{escape(side_effect)}</p>
      {qr_panel}
    </section>
    """


def _side_effect_summary(transaction: Transaction, db_path: str | Path | None) -> str:
    """Return a concise ledger side-effect summary."""
    if transaction.transaction_type == "sale" and transaction.item and transaction.quantity is not None:
        return f"Stock reduced by {_format_quantity(transaction.quantity)} {transaction.item}."
    if transaction.transaction_type == "inventory_purchase" and transaction.item and transaction.quantity is not None:
        return f"Stock increased by {_format_quantity(transaction.quantity)} {transaction.item}."
    if transaction.transaction_type == "customer_credit" and transaction.customer:
        return f"{transaction.customer}'s outstanding balance increased."
    if transaction.transaction_type == "customer_payment" and transaction.customer:
        return f"{transaction.customer}'s outstanding balance decreased."
    if transaction.transaction_type == "expense":
        return "Expense included in today's costs."
    return "Ledger, dashboard, customer credit, and inventory views refreshed."


def _status_message(
    transaction: Transaction,
    source_message: str = "Parsed transaction.",
    fallback_reason: str | None = None,
    prefix: str | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Return a human-readable parsing status."""
    parts = []
    parts.append(_source_chip(source_message, fallback_reason))
    parts.append(_language_confidence_chip(transaction))
    if prefix:
        parts.append(prefix)
    parts.append(source_message)
    if fallback_reason:
        parts.append(f"Fallback reason: `{fallback_reason}`.")

    if transaction.transaction_type == "unknown":
        parts.append("Could not confidently parse this note. You can still inspect the structured output.")
    else:
        parts.append(f"Parsed as `{transaction.transaction_type}` with confidence `{transaction.confidence:.2f}`.")
    if warnings:
        parts.append("Review warnings: " + ", ".join(warnings) + ".")
    return " ".join(parts)


def _source_chip(source_message: str, fallback_reason: str | None = None) -> str:
    """Return a visual parse-source chip for Markdown/HTML status output."""
    if fallback_reason or "local" in source_message.lower() or "fallback" in source_message.lower():
        return '<span class="vl-status-chip vl-status-chip-fallback">Local fallback</span>'
    if "modal" in source_message.lower() or "nemotron" in source_message.lower():
        return '<span class="vl-status-chip vl-status-chip-cloud">Cloud AI</span>'
    return '<span class="vl-status-chip">Parsed</span>'


def _language_confidence_chip(transaction: Transaction) -> str:
    """Return a compact language/confidence chip for parse status."""
    language = _detect_note_language(transaction.notes)
    confidence_label = "High confidence" if transaction.confidence >= 0.85 else "Needs review"
    return f'<span class="vl-status-chip vl-status-chip-language">{escape(language)} · {confidence_label}</span>'


def _detect_note_language(note: str | None) -> str:
    """Detect a lightweight language label from common seller note phrases."""
    text = (note or "").lower()
    if any(token in text for token in ("vendí", "pagué", " debe ", " pagó", " cada uno", "suministros")):
        return "Spanish"
    if any(token in text for token in ("vendu", "payé", " doit ", " a payé", "chacun", "fournitures", "acheté")):
        return "French"
    if any(token in text for token in ("vendi", "paguei", " deve ", "pagou", "suprimentos", "comprei")):
        return "Portuguese"
    if any(token in text for token in ("dene hai", "dena hai", "diya", "kharida", "chukaya")):
        return "Hinglish"
    if any(token in text for token in ("lidha", "aapva che", "apvana che", "aapya")):
        return "Gujarati-lite"
    return "English"


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
