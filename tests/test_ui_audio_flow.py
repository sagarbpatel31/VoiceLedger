import pytest

pytest.importorskip("gradio")

from voiceledger.ui import gradio_app


def test_transcribe_and_parse_audio_handles_transcription_error(monkeypatch) -> None:
    def fail_transcription(_: str | None) -> str:
        raise gradio_app.TranscriptionError("test failure")

    monkeypatch.setattr(gradio_app, "transcribe_audio", fail_transcription)

    transcript, structured, state, status = gradio_app._transcribe_and_parse_audio("audio.wav")

    assert transcript == ""
    assert structured["transaction_type"] == "unknown"
    assert state is None
    assert status == "Transcription failed: test failure"


def test_transcribe_and_parse_audio_parses_transcript(monkeypatch) -> None:
    monkeypatch.setattr(
        gradio_app,
        "transcribe_audio",
        lambda _: "Sold 12 mangoes, 20 each",
    )

    transcript, structured, state, status = gradio_app._transcribe_and_parse_audio("audio.wav")

    assert transcript == "Sold 12 mangoes, 20 each"
    assert structured["transaction_type"] == "sale"
    assert structured["amount"] == 240
    assert state == structured
    assert "sale" in status
