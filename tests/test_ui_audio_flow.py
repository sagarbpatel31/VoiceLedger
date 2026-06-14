import pytest

pytest.importorskip("gradio")

from backend.modal_api import ParseResult, TranscriptionResult
from voiceledger.ui import gradio_app


def test_create_app_builds_blocks(tmp_path) -> None:
    app = gradio_app.create_app(tmp_path / "voiceledger.sqlite3")

    try:
        assert app is not None
    finally:
        app.close()


def test_transcribe_and_parse_audio_handles_transcription_error(monkeypatch) -> None:
    def fail_transcription(_: object) -> str:
        raise RuntimeError("test failure")

    monkeypatch.setattr(gradio_app.modal_api, "transcribe_audio_result", lambda audio, fallback, **kwargs: fail_transcription(audio))

    transcript, structured, state, status, review_card = gradio_app._transcribe_and_parse_audio("audio.wav")

    assert transcript == ""
    assert structured["transaction_type"] == "unknown"
    assert state is None
    assert status == "Transcription failed: test failure"
    assert "Transaction review" in review_card


def test_transcribe_and_parse_audio_parses_transcript(monkeypatch) -> None:
    monkeypatch.setattr(
        gradio_app.modal_api,
        "transcribe_audio_result",
        lambda audio, fallback, **kwargs: TranscriptionResult(
            transcript="Sold 12 mangoes, 20 each",
            source="modal",
            message="Transcribed by Modal faster-whisper endpoint.",
        ),
    )
    monkeypatch.setattr(
        gradio_app.modal_api,
        "parse_transaction_result",
        lambda text, fallback, **kwargs: ParseResult(
            transaction=fallback(text),
            source="local",
            message="Parsed locally with the rule parser after Modal failed.",
            fallback_reason="test fallback",
        ),
    )

    transcript, structured, state, status, review_card = gradio_app._transcribe_and_parse_audio("audio.wav")

    assert transcript == "Sold 12 mangoes, 20 each"
    assert structured["transaction_type"] == "sale"
    assert structured["amount"] == 240
    assert state == structured
    assert "sale" in status
    assert "Modal faster-whisper" in status
    assert "test fallback" in status
    assert "Review transaction" in review_card


def test_parse_note_surfaces_modal_source(monkeypatch) -> None:
    monkeypatch.setattr(
        gradio_app.modal_api,
        "parse_transaction_result",
        lambda text, fallback, **kwargs: ParseResult(
            transaction=fallback(text),
            source="modal",
            message="Parsed by Modal using NVIDIA Nemotron.",
        ),
    )

    structured, state, status, review_card = gradio_app._parse_note("Paid 500 for supplies")

    assert structured["transaction_type"] == "expense"
    assert state == structured
    assert "NVIDIA Nemotron" in status
    assert "Safe to save" in review_card


def test_parse_note_local_mode_surfaces_local_fallback(monkeypatch) -> None:
    captured = {}

    def fake_parse(text, fallback, **kwargs):
        captured.update(kwargs)
        return ParseResult(
            transaction=fallback(text),
            source="local",
            message="Parsed locally with the rule parser.",
            fallback_reason="Cloud AI is disabled for local-first mode.",
        )

    monkeypatch.setattr(gradio_app.modal_api, "parse_transaction_result", fake_parse)

    structured, state, status, review_card = gradio_app._parse_note("Amit owes 100", ai_mode="Local fallback only")

    assert captured["force_local"] is True
    assert structured["transaction_type"] == "customer_credit"
    assert state == structured
    assert "Local fallback" in status
    assert "local-first mode" in status
    assert "Safe to save" in review_card


def test_parse_note_surfaces_language_confidence_chip(monkeypatch) -> None:
    monkeypatch.setattr(
        gradio_app.modal_api,
        "parse_transaction_result",
        lambda text, fallback, **kwargs: ParseResult(
            transaction=fallback(text),
            source="local",
            message="Parsed locally with the rule parser.",
        ),
    )

    _, _, status, _ = gradio_app._parse_note("Vendí 12 mangos, 20 cada uno")

    assert "Spanish" in status
    assert "High confidence" in status


def test_high_contrast_demo_panels_are_rendered() -> None:
    panel = gradio_app._info_panel(
        "Demo Health",
        "The Space calls Modal first for speech and NVIDIA Nemotron parsing, with local fallback for reliability.",
    )

    assert "vl-info-panel" in panel
    assert "Demo Health" in panel
    assert "NVIDIA Nemotron" in panel


def test_judge_demo_panel_surfaces_submission_flow() -> None:
    panel = gradio_app._judge_demo_panel()

    assert "Judge Demo Flow" in panel
    assert "1. Seed demo data" in panel
    assert "2. Record/type" in panel
    assert "3. Save" in panel
    assert "4. View dashboard/reports" in panel
    assert "NVIDIA Nemotron parser" in panel


def test_submission_story_surfaces_pipeline_and_small_model_fit() -> None:
    story = gradio_app._submission_story_panel()
    pipeline = gradio_app._ai_pipeline_strip()
    small_model = gradio_app._small_model_fit_card()

    assert "Built for a real informal seller" in story
    assert "Small Model Intelligence" in pipeline
    assert "Nemotron 4B" in pipeline
    assert "Fallback" in pipeline
    assert "Database" in pipeline
    assert "Why Small Models Win Here" in small_model
    assert "Speed & Latency" in small_model
    assert "Localization" in small_model


def test_demo_health_placeholder_includes_nemotron_status() -> None:
    placeholder = gradio_app._demo_health_placeholder()

    assert "NVIDIA Nemotron parser" in set(placeholder["check"])


def test_show_page_makes_exactly_one_section_visible() -> None:
    updates = gradio_app._show_page("ledger")

    assert len(updates) == 10
    assert updates[-1]["visible"] is True
    assert sum(1 for update in updates if update["visible"]) == 1


def test_review_warnings_flag_missing_and_low_confidence() -> None:
    transaction = gradio_app.Transaction(transaction_type="unknown", confidence=0.2)

    warnings = gradio_app._review_warnings(transaction, None)

    assert "Unknown type" in warnings
    assert "Low confidence" in warnings


def test_review_card_surfaces_needs_review_for_missing_fields() -> None:
    transaction = gradio_app.Transaction(transaction_type="customer_credit", confidence=0.8)

    review_card = gradio_app._review_card(transaction, "Parsed locally.", gradio_app._review_warnings(transaction, None))

    assert "Needs review" in review_card
    assert "Missing amount" in review_card
    assert "Missing customer" in review_card


def test_parse_note_for_editing_populates_review_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        gradio_app.modal_api,
        "parse_transaction_result",
        lambda text, fallback, **kwargs: ParseResult(
            transaction=fallback(text),
            source="local",
            message="Parsed locally with the rule parser.",
        ),
    )

    result = gradio_app._parse_note_for_editing("Sold 12 mangoes, 20 each")

    assert result[0]["transaction_type"] == "sale"
    assert result[4] == "sale"
    assert result[5] == "mangoes"
    assert result[6] == 12
    assert result[8] == 240


def test_price_memory_fills_missing_sale_price(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Sold 12 mangoes, 20 each"), db_path)
    monkeypatch.setattr(
        gradio_app.modal_api,
        "parse_transaction_result",
        lambda text, fallback, **kwargs: ParseResult(
            transaction=fallback(text),
            source="local",
            message="Parsed locally with the rule parser.",
        ),
    )

    result = gradio_app._parse_note_for_editing("Sold 5 mangoes", db_path)

    assert result[0]["unit_price"] == 20
    assert result[0]["amount"] == 100
    assert result[7] == 20
    assert result[8] == 100
    assert "Price memory used" in result[3]


def test_price_memory_does_not_overwrite_explicit_price(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Sold 12 mangoes, 20 each"), db_path)
    transaction = gradio_app.local_parse_transaction("Sold 5 mangoes, 30 each")

    updated, used = gradio_app.suggest_price_from_history(transaction, db_path)

    assert used is False
    assert updated.unit_price == 30
    assert updated.amount == 150


def test_apply_review_edits_updates_payload_and_review_card(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    parsed = gradio_app.local_parse_transaction("Sold 12 mangoes, 20 each").model_dump()

    payload, state, status, review_card = gradio_app._apply_review_edits(
        parsed,
        "sale",
        "mangoes",
        10,
        25,
        250,
        None,
        "paid",
        "Sold 10 mangoes, 25 each",
        0.95,
        db_path,
    )

    assert payload["quantity"] == 10
    assert payload["amount"] == 250
    assert state == payload
    assert "Review updated" in status
    assert "250" in review_card
    correction_log = gradio_app.get_correction_log(db_path)
    assert len(correction_log) == 1
    assert "quantity" in correction_log.iloc[0]["changed_fields"]


def test_receipt_card_summarizes_saved_sale(tmp_path) -> None:
    transaction = gradio_app.local_parse_transaction("Sold 12 mangoes, 20 each")

    receipt = gradio_app._receipt_card(transaction, 4, tmp_path / "voiceledger.sqlite3")

    assert "Saved just now" in receipt
    assert "Transaction #4" in receipt
    assert "Stock reduced" in receipt


def test_daily_closeout_returns_exports(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Sold 12 mangoes, 20 each"), db_path)

    summary, pdf_path, csv_path, whatsapp, status = gradio_app._run_daily_closeout(db_path)

    assert "Daily Closeout Ready" in summary
    assert pdf_path is not None
    assert csv_path is not None
    assert "VoiceLedger Seller Daily Summary" in whatsapp
    assert "Daily closeout complete" in status


def test_command_center_and_seller_setup_use_settings(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.update_business_settings(
        business_name="Mango Cart",
        currency_symbol="Rs ",
        low_stock_threshold=3,
        language_style="English + Hinglish",
        db_path=db_path,
    )
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Sold 12 mangoes, 20 each"), db_path)

    command_center = gradio_app._command_center(db_path)

    assert "Mango Cart Command Center" in command_center
    assert "Rs240" in command_center


def test_customer_followup_and_reorder_helpers(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Amit owes 100"), db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Amit paid 40"), db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Bought 3 onions"), db_path)

    followup = gradio_app.generate_customer_followup("Amit", db_path)
    reorder, message = gradio_app.generate_reorder_list(db_path)

    assert "Amit" in followup
    assert "₹60" in followup
    assert "onions" in set(reorder["item"])
    assert "Onions" in message


def test_debt_reminder_queue_sorts_positive_balances(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Amit owes 100"), db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Ramesh owes 250"), db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Amit paid 40"), db_path)

    queue = gradio_app.get_debt_reminder_queue(db_path)
    reminder = gradio_app.generate_debt_reminder("Ramesh", db_path)

    assert list(queue["customer"]) == ["Ramesh", "Amit"]
    assert "₹250" in queue.iloc[0]["suggested_message"]
    assert "Ramesh" in reminder


def test_reorder_intelligence_flags_low_and_fast_stock(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.update_business_settings(low_stock_threshold=5, db_path=db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Bought 3 onions"), db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Bought 20 mangoes"), db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Sold 12 mangoes, 20 each"), db_path)

    recommendations = gradio_app.generate_reorder_intelligence(db_path)
    table, message = gradio_app._generate_reorder_intelligence_for_ui(db_path)

    statuses = dict(zip(recommendations["item"], recommendations["status"], strict=True))
    assert statuses["onions"] == "Low stock"
    assert statuses["mangoes"] == "Selling fast"
    assert "recent_sold" in table.columns
    assert "Mangoes" in message


def test_currency_presets_and_voice_commands(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Amit owes 100"), db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Bought 3 onions"), db_path)

    assert gradio_app._currency_symbol_for_preset("Brazil - BRL (R$)") == "R$"
    assert gradio_app._currency_preset_for_symbol("€") == "European Union - EUR (€)"
    assert "Amit" in gradio_app._run_voice_command("show Amit", db_path)
    assert "onions" in gradio_app._run_voice_command("stock onions", db_path)
    assert "Daily Closeout Ready" in gradio_app._run_voice_command("close today", db_path)


def test_insight_coach_surfaces_credit_and_stock_actions(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Amit owes 100"), db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Bought 3 onions"), db_path)

    coach = gradio_app._insight_coach(db_path)

    assert "Insight Coach" in coach
    assert "Follow up with Amit" in coach
    assert "Restock onions" in coach


def test_field_test_evidence_persists_checklist_and_notes(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    status = gradio_app._save_field_test_evidence(
        ["Record sale", "Export report"],
        "Local snack seller",
        "Voice sale and PDF export",
        "Moved corrections before save",
        db_path,
    )
    settings = gradio_app.get_business_settings(db_path)

    assert "2 checklist item" in status
    assert settings["field_test_who"] == "Local snack seller"
    assert gradio_app._field_test_checklist_values(settings) == ["Record sale", "Export report"]


def test_field_test_evidence_persists_real_user_details(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    status = gradio_app._save_field_test_evidence(
        ["Record sale"],
        "Local seller",
        "Voice note",
        "Old change note",
        db_path,
        pain_point="Paper notes get lost",
        before="Used memory",
        after="Checks dashboard",
        useful="Debt reminders",
        changed_after_feedback="Added price memory",
    )
    settings = gradio_app.get_business_settings(db_path)

    assert "Paper notes get lost" in status
    assert settings["field_pain_point"] == "Paper notes get lost"
    assert settings["field_before"] == "Used memory"
    assert settings["field_after"] == "Checks dashboard"
    assert settings["field_useful_moments"] == "Debt reminders"
    assert settings["field_changed_after_feedback"] == "Added price memory"


def test_guided_demo_status_reflects_progress(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    empty_status = gradio_app.get_guided_demo_status(db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Sold 12 mangoes, 20 each"), db_path)
    progressed_status = gradio_app.get_guided_demo_status(db_path)

    assert "Guided Judge Mode" in empty_status
    assert "Seed Demo Data" in progressed_status
    assert "Done" in progressed_status
