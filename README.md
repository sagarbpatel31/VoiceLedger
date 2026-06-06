# VoiceLedger

VoiceLedger is a voice-first and text-assisted bookkeeping MVP for informal sellers, street vendors, home businesses, and small shop owners.

The current version focuses on a clean, deterministic foundation:

- Record a transaction with your microphone and transcribe it with faster-whisper.
- Type or paste a transaction note.
- Parse it with simple rules.
- Save the structured transaction to SQLite.
- View the ledger, customer credit book, and inventory in a Gradio interface.
- Monitor business insights in a dashboard.
- Download a Daily Summary PDF report.

LLM parsing is intentionally not implemented yet.

## Examples

| Input | Parsed result |
| --- | --- |
| `Sold 12 mangoes, 20 each` | Sale, quantity `12`, item `mangoes`, unit price `20`, amount `240` |
| `Paid 500 for supplies` | Expense, amount `500`, item `supplies` |
| `Bought 50 mangoes` | Inventory purchase, quantity `50`, item `mangoes` |
| `Amit owes 100` | Customer credit, customer `Amit`, amount `100` |
| `Amit paid 50` | Customer payment, customer `Amit`, amount `50` |

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
pytest
```

## Notes

- Speech transcription uses the faster-whisper `small` model and loads lazily on first use.
- LLM parsing is not wired up yet.
- The parser is intentionally transparent and easy to extend for hackathon iteration.
- Customer credit balances are updated when parsed customer credit or payment transactions are saved.
- Inventory stock is updated when parsed inventory purchases or sales are saved.
- PDF reports are generated with fpdf2 from the current SQLite ledger state.
- Parser architecture supports rule-based and Hugging Face Inference API compatible LLM parsers, with rule fallback on LLM failure.
- The dashboard shows daily sales, expenses, profit, outstanding credit, top sellers, and low-stock alerts from saved data.
