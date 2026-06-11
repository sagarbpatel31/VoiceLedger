"""Speech-to-text support using faster-whisper."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from collections.abc import Iterable
from typing import Any, Protocol


MODEL_SIZE = "small"


class WhisperModelProtocol(Protocol):
    """Minimal protocol for the faster-whisper model used by this module."""

    def transcribe(self, audio: str, **kwargs: object) -> tuple[Iterable["WhisperSegmentProtocol"], object]:
        """Transcribe an audio file."""


class WhisperSegmentProtocol(Protocol):
    """Minimal protocol for faster-whisper transcript segments."""

    text: str


class TranscriptionError(RuntimeError):
    """Raised when audio transcription fails."""


def transcribe_audio(audio_path: Any) -> str:
    """Transcribe an audio file with the faster-whisper small model.

    The model is loaded lazily and cached after the first call. This keeps the
    Gradio app responsive at startup while still using the requested small
    open-source speech model for actual transcription.
    """
    path = _coerce_audio_path(audio_path)
    if path is None:
        raise TranscriptionError("No audio file was provided.")

    if not path.exists():
        raise TranscriptionError(f"Audio file does not exist: {path}")

    try:
        model = _get_model()
        segments, _ = model.transcribe(
            str(path),
            beam_size=5,
            vad_filter=True,
        )
        transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
    except TranscriptionError:
        raise
    except Exception as exc:  # pragma: no cover - depends on local model/runtime state.
        raise TranscriptionError(f"Could not transcribe audio: {exc}") from exc

    if not transcript:
        raise TranscriptionError("No speech was detected in the audio.")

    return transcript.strip()


def _coerce_audio_path(audio_value: Any) -> Path | None:
    """Extract a local audio filepath from Gradio audio values."""
    if audio_value is None:
        return None
    if isinstance(audio_value, (str, Path)):
        return Path(audio_value)
    if isinstance(audio_value, dict):
        for key in ("path", "name", "file", "filepath"):
            value = audio_value.get(key)
            if value:
                return Path(value)
    if isinstance(audio_value, (list, tuple)):
        for value in audio_value:
            path = _coerce_audio_path(value)
            if path is not None:
                return path
    return None


@lru_cache(maxsize=1)
def _get_model() -> WhisperModelProtocol:
    """Load and cache the faster-whisper small model."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - environment dependent.
        raise TranscriptionError(
            "faster-whisper is not installed. Install dependencies from requirements.txt."
        ) from exc

    return WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
