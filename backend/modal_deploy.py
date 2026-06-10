"""Modal deployment for VoiceLedger speech and Nemotron parsing endpoints.

Deploy with:
    modal deploy backend/modal_deploy.py
"""

from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import modal


NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-4B")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi[standard]>=0.115.0",
        "faster-whisper>=1.1.0",
        "huggingface_hub>=0.26.0",
        "pandas>=2.2.0",
        "pydantic>=2.7.0",
    )
    .add_local_python_source("voiceledger", copy=True)
)

app = modal.App("voiceledger-backend")


@app.function(
    image=image,
    gpu="T4",
    timeout=600,
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
@modal.asgi_app(label="voiceledger-api")
def api():
    """Serve VoiceLedger Modal API routes."""
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from pydantic import BaseModel

    from voiceledger.parser.llm_parser import SYSTEM_PROMPT
    from voiceledger.parser.rules import parse_transaction as rule_parse_transaction
    from voiceledger.parser.schema import Transaction

    web_app = FastAPI(title="VoiceLedger Modal API")

    class ParseRequest(BaseModel):
        text: str

    @web_app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @web_app.post("/transcribe")
    async def transcribe(audio: UploadFile = File(...)) -> dict[str, str]:
        audio_bytes = await audio.read()
        suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_path = temp_audio.name

            model = _get_whisper_model()
            segments, _ = model.transcribe(
                temp_path,
                beam_size=5,
                vad_filter=True,
                language="en",
            )
            transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
        finally:
            if "temp_path" in locals():
                Path(temp_path).unlink(missing_ok=True)

        if not transcript:
            raise HTTPException(status_code=422, detail="No speech detected.")
        return {"transcript": transcript.strip()}

    @web_app.post("/parse")
    def parse(request: ParseRequest) -> dict[str, Any]:
        text = request.text.strip()
        if not text:
            return {"transaction": Transaction(notes="", confidence=0.0).model_dump()}

        try:
            generated_text = _generate_nemotron_json(text, SYSTEM_PROMPT)
            payload = _extract_json_object(generated_text)
            transaction = Transaction.model_validate(payload)
            if not transaction.notes:
                transaction = transaction.model_copy(update={"notes": text})
        except Exception:
            transaction = rule_parse_transaction(text)

        return {"transaction": transaction.model_dump()}

    return web_app


@lru_cache(maxsize=1)
def _get_whisper_model():
    """Load faster-whisper small once per warm Modal container."""
    from faster_whisper import WhisperModel

    return WhisperModel("small", device="cuda", compute_type="float16")


@lru_cache(maxsize=1)
def _get_hf_client():
    """Create a Hugging Face Inference client for Nemotron."""
    from huggingface_hub import InferenceClient

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    return InferenceClient(model=NEMOTRON_MODEL, token=token)


def _generate_nemotron_json(text: str, system_prompt: str) -> str:
    """Generate strict JSON transaction output with Nemotron."""
    prompt = f"{system_prompt}\n\nUser text: {text}\nJSON:"
    return _get_hf_client().text_generation(
        prompt,
        max_new_tokens=256,
        temperature=0.0,
        return_full_text=False,
    )


def _extract_json_object(response: str) -> dict[str, Any]:
    """Extract a JSON object from model output."""
    start = response.find("{")
    end = response.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Model response did not contain JSON.")

    payload = json.loads(response[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Model response JSON must be an object.")
    return payload
