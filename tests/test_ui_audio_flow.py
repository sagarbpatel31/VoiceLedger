import pytest

pytest.importorskip("gradio")

from backend.modal_api import ParseResult, TranscriptionResult
from voiceledger.ui import gradio_app


def test_transcribe_and_parse_audio_handles_transcription_error(monkeypatch) -> None:
    def fail_transcription(_: object) -> str:
        raise RuntimeError("test failure")

    monkeypatch.setattr(gradio_app.modal_api, "transcribe_audio_result", lambda audio, fallback: fail_transcription(audio))

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
        lambda audio, fallback: TranscriptionResult(
            transcript="Sold 12 mangoes, 20 each",
            source="modal",
            message="Transcribed by Modal faster-whisper endpoint.",
        ),
    )
    monkeypatch.setattr(
        gradio_app.modal_api,
        "parse_transaction_result",
        lambda text, fallback: ParseResult(
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
        lambda text, fallback: ParseResult(
            transaction=fallback(text),
            source="modal",
            message="Parsed by Modal using NVIDIA Nemotron.",
        ),
    )

    structured, state, status, review_card = gradio_app._parse_note("Paid 500 for supplies")

    assert structured["transaction_type"] == "expense"
    assert state == structured
    assert "NVIDIA Nemotron" in status
    assert "Ready to save" in review_card


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
    assert "VoiceLedger Daily Summary" in whatsapp
    assert "Daily closeout complete" in status
