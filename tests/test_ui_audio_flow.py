import pytest

pytest.importorskip("gradio")

from backend.modal_api import ParseResult, TranscriptionResult
from voiceledger.ui import gradio_app


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
    assert "AI pipeline" in pipeline
    assert "NVIDIA Nemotron" in pipeline
    assert "Rule fallback" in pipeline
    assert "SQLite ledger" in pipeline
    assert "Why small models fit" in small_model
    assert "Constrained task" in small_model
    assert "Deterministic ledger" in small_model


def test_demo_health_placeholder_includes_nemotron_status() -> None:
    placeholder = gradio_app._demo_health_placeholder()

    assert "NVIDIA Nemotron parser" in set(placeholder["check"])


def test_show_page_makes_exactly_one_section_visible() -> None:
    updates = gradio_app._show_page("ledger")

    assert len(updates) == 9
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


def test_insight_coach_surfaces_credit_and_stock_actions(tmp_path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Amit owes 100"), db_path)
    gradio_app.add_transaction(gradio_app.local_parse_transaction("Bought 3 onions"), db_path)

    coach = gradio_app._insight_coach(db_path)

    assert "Insight Coach" in coach
    assert "Follow up with Amit" in coach
    assert "Restock onions" in coach
