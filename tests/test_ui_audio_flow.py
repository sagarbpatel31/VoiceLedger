import pytest

pytest.importorskip("gradio")

from backend.modal_api import ParseResult, TranscriptionResult
from voiceledger.ui import gradio_app


def test_transcribe_and_parse_audio_handles_transcription_error(monkeypatch) -> None:
    def fail_transcription(_: object) -> str:
        raise RuntimeError("test failure")

    monkeypatch.setattr(gradio_app.modal_api, "transcribe_audio_result", lambda audio, fallback: fail_transcription(audio))

    transcript, structured, state, status = gradio_app._transcribe_and_parse_audio("audio.wav")

    assert transcript == ""
    assert structured["transaction_type"] == "unknown"
    assert state is None
    assert status == "Transcription failed: test failure"


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

    transcript, structured, state, status = gradio_app._transcribe_and_parse_audio("audio.wav")

    assert transcript == "Sold 12 mangoes, 20 each"
    assert structured["transaction_type"] == "sale"
    assert structured["amount"] == 240
    assert state == structured
    assert "sale" in status
    assert "Modal faster-whisper" in status
    assert "test fallback" in status


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

    structured, state, status = gradio_app._parse_note("Paid 500 for supplies")

    assert structured["transaction_type"] == "expense"
    assert state == structured
    assert "NVIDIA Nemotron" in status


def test_high_contrast_demo_panels_are_rendered() -> None:
    panel = gradio_app._info_panel(
        "Demo Health",
        "The Space calls Modal first for speech and NVIDIA Nemotron parsing, with local fallback for reliability.",
    )

    assert "vl-info-panel" in panel
    assert "Demo Health" in panel
    assert "NVIDIA Nemotron" in panel


def test_show_page_makes_exactly_one_section_visible() -> None:
    updates = gradio_app._show_page("ledger")

    assert len(updates) == 9
    assert updates[-1]["visible"] is True
    assert sum(1 for update in updates if update["visible"]) == 1
