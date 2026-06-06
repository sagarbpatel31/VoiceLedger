from pathlib import Path

import pytest

from voiceledger.speech.transcribe import TranscriptionError, transcribe_audio


def test_transcribe_audio_requires_audio_path() -> None:
    with pytest.raises(TranscriptionError, match="No audio file"):
        transcribe_audio(None)


def test_transcribe_audio_requires_existing_file(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.wav"

    with pytest.raises(TranscriptionError, match="does not exist"):
        transcribe_audio(missing_file)
