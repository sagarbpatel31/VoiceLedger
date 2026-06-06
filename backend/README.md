# VoiceLedger Modal Backend

This directory contains the optional Modal deployment used by the Hugging Face Space for heavier AI workloads.

## Endpoints

Deploying `backend/modal_deploy.py` creates a FastAPI app with:

- `POST /transcribe` - accepts an uploaded audio file and returns `{"transcript": "..."}`
- `POST /parse` - accepts `{"text": "..."}` and returns `{"transaction": {...}}`
- `GET /health` - basic health check

The Space calls these endpoints through `backend/modal_api.py`. If an endpoint is not configured or a request fails, VoiceLedger falls back to local faster-whisper or the rule parser.

## Modal Setup

Install Modal locally:

```bash
pip install modal
modal setup
```

Create a Modal secret named `huggingface-secret` with a Hugging Face token:

```bash
modal secret create huggingface-secret HF_TOKEN=hf_your_token_here
```

Deploy:

```bash
modal deploy backend/modal_deploy.py
```

Set these Hugging Face Space environment variables after deployment:

```bash
VOICELEDGER_MODAL_TRANSCRIBE_URL=https://your-modal-url/transcribe
VOICELEDGER_MODAL_PARSE_URL=https://your-modal-url/parse
VOICELEDGER_MODAL_API_TOKEN=optional-shared-token
```

`VOICELEDGER_MODAL_API_TOKEN` is optional for the current deployment file. Add matching auth checks in `backend/modal_deploy.py` before using it for a public production endpoint.

## Model Configuration

The deployment uses:

- faster-whisper `small` for speech-to-text
- `nvidia/NVIDIA-Nemotron-3-Nano-4B` through Hugging Face Inference by default

Override the parser model with:

```bash
NEMOTRON_MODEL=your/hf-model-id modal deploy backend/modal_deploy.py
```
