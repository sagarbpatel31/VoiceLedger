---
title: VoiceLedger
emoji: 📉
colorFrom: yellow
colorTo: green
sdk: gradio
sdk_version: 6.17.3
python_version: '3.13'
app_file: app.py
pinned: false
short_description: voice bookkeeping for informal sellers
---

# VoiceLedger

VoiceLedger is a voice-first bookkeeping app for informal sellers, street vendors, home businesses, and small shop owners who track sales, customer dues, stock, and daily profit from quick spoken or typed notes.

The submission version is feature-frozen around the complete demo loop:

- Record a transaction with your microphone and transcribe it with faster-whisper.
- Type or paste a transaction note.
- Bulk import multiple pasted notes for review and editing.
- Parse it with Modal-hosted NVIDIA Nemotron when configured, with local rules as a deterministic fallback.
- Save the structured transaction to SQLite.
- View the ledger, customer credit book, and inventory in a Gradio interface.
- Monitor business insights in a dashboard.
- Use a mobile-first, business-style Gradio interface with custom styling.
- Download a Daily Summary PDF report.
- Generate a WhatsApp-ready daily business summary.
- Offload speech transcription and LLM parsing to optional Modal endpoints.
- Edit or delete saved transactions while keeping customer credit and inventory balances consistent.
- Export the ledger as CSV for spreadsheet sharing.

When Modal endpoints are configured, parsing runs through the Modal backend using `nvidia/NVIDIA-Nemotron-3-Nano-4B` via Hugging Face Inference. If Modal is unavailable or returns an invalid response, VoiceLedger falls back to the local rule parser for demo reliability.

VoiceLedger is designed for the Build Small Hackathon Backyard AI track: a concrete, real-world bookkeeping problem for informal sellers and home businesses. The demo story is anonymized around a local seller who tracks sales, customer dues, stock, and daily profit from short voice notes.

## Judge Demo Flow

Use the `Sections` navigation in the Space:

1. `Record Text & Voice`: click `Seed Demo Transactions`, then type or speak `Sold 12 mangoes, 20 each`.
2. Parse and save the reviewed transaction; the status line shows Modal/NVIDIA Nemotron or local fallback.
3. Open `Dashboard`, `Customer Credit`, `Inventory`, and `Ledger` to show automatic bookkeeping updates.
4. Open `Reports & PDF` to download the PDF, generate the WhatsApp summary, and use `Ledger` to export CSV.
5. Open `Demo Health` to show Modal backend status, deployed backend version, NVIDIA Nemotron parser status, SQLite, PDF support, and configured endpoints.

## Example Inputs

Try these in `Record Text & Voice` or paste them together in `Bulk Import`:

```text
Sold 12 mangoes, 20 each
Paid 500 for supplies
Amit owes 100
Bought 50 mangoes
```

The same examples are available in `sample_data/demo_transactions.txt`.

## Examples

| Input | Parsed result |
| --- | --- |
| `Sold 12 mangoes, 20 each` | Sale, quantity `12`, item `mangoes`, unit price `20`, amount `240` |
| `mango 12 x 20` | Sale, quantity `12`, item `mango`, unit price `20`, amount `240` |
| `Paid 500 for supplies` | Expense, amount `500`, item `supplies` |
| `rent 300` | Expense, amount `300`, item `rent` |
| `Bought 50 mangoes` | Inventory purchase, quantity `50`, item `mangoes` |
| `Amit owes 100` | Customer credit, customer `Amit`, amount `100` |
| `Amit paid 50` | Customer payment, customer `Amit`, amount `50` |

## Demo Script

1. Use the `Hackathon Demo Launchpad` on the first screen to seed demo transactions.
2. Open `Record Text & Voice`, speak or type `Sold 12 mangoes, 20 each`, parse it, and save it.
3. Show the parse status: Modal/NVIDIA Nemotron when available, local fallback when needed.
4. Open `Dashboard`, `Customer Credit`, and `Inventory` to show automatic bookkeeping updates.
5. Open `Ledger`, load a transaction by id, update or delete it, then show refreshed balances.
6. Download CSV from `Ledger`, generate the PDF and WhatsApp summary from `Reports & PDF`.
7. Click `Check Demo Health` from the launchpad, or open `Demo Health`, to show Modal health, deployed backend version, Nemotron status, database, PDF, and endpoint checks.

## Screenshot and GIF Moments

Capture these three moments for the Space README, demo video, or social post:

- `Record Text & Voice`: seeded demo data, transaction input, structured output, and parse source.
- `Dashboard`: metrics, top-selling item, low-stock table, and outstanding credit.
- `Reports & PDF` plus `Ledger`: PDF/WhatsApp export and CSV download.

Supporting submission assets:

- `docs/demo-video-script.md`
- `docs/submission-checklist.md`
- `docs/social-post.md`
- `docs/field-notes.md`

## Repository Structure

```text
.
├── app.py
├── requirements.txt
├── README.md
├── voiceledger/
│   ├── speech/
│   ├── parser/
│   ├── ledger/
│   ├── reports/
│   ├── ui/
│   └── config.py
└── tests/
```

## Local Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

By default, the SQLite database is created at `data/voiceledger.sqlite3`. Override it with:

```bash
export VOICELEDGER_DB_PATH=/path/to/voiceledger.sqlite3
```

## Run Tests

```bash
env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest
```

## Modal Backend Checks

After deploying `backend/modal_deploy.py`, verify the live backend:

```bash
curl https://sagarpat3199--voiceledger-api.modal.run/health
curl https://sagarpat3199--voiceledger-api.modal.run/version
curl -X POST https://sagarpat3199--voiceledger-api.modal.run/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"Sold 12 mangoes, 20 each"}'
```

## Notes

- Speech transcription uses the faster-whisper `small` model and loads lazily on first use.
- LLM parsing is wired through the optional Modal backend using NVIDIA Nemotron, with rule parsing as fallback.
- The parser is intentionally transparent and easy to extend for hackathon iteration.
- Customer credit balances are updated when parsed customer credit or payment transactions are saved.
- Inventory stock is updated when parsed inventory purchases or sales are saved.
- PDF reports are generated with fpdf2 from the current SQLite ledger state.
- Parser architecture supports rule-based and Hugging Face Inference API compatible LLM parsers, with rule fallback on LLM failure.
- The dashboard shows daily sales, expenses, profit, outstanding credit, top sellers, and low-stock alerts from saved data.
- WhatsApp summaries provide a short copyable daily recap for sharing.
- Bulk import splits pasted notes by line, parses each line, supports review edits, and saves all reviewed transactions.
- Modal integration lives in `backend/`; if endpoint URLs are not configured, local fallback stays active.
- NVIDIA Nemotron 3 Nano 4B is used by the Modal parser endpoint and is also available as a local `transformers` parser provider for strict JSON transaction extraction.
- The Demo Health section checks Modal reachability, deployed backend version, NVIDIA Nemotron parser status, SQLite availability, PDF support, and configured endpoint status.
- Ledger edits and deletes rebuild customer balances and inventory from saved transactions to avoid stale side effects.
- CSV export downloads all ledger rows in the same column order as the app table.
- The UI uses a custom theme, responsive spacing, and dashboard cards instead of the default Gradio look.
