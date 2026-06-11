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
- Configure seller context: business name, currency label, low-stock threshold, and language style.
- Use a first-run “Start in 60 seconds” guide for setup, first transaction, review, and closeout.
- Type or paste a transaction note.
- Bulk import multiple pasted notes for review and editing.
- Parse it with Modal-hosted NVIDIA Nemotron when configured, with local rules as a deterministic fallback.
- Parse common English, Hinglish, Hindi-lite, Gujarati-lite, Spanish, French, and Portuguese seller phrases with deterministic fallback rules.
- Review a human-friendly transaction card with warning badges before saving.
- Correct transaction type, item, customer, quantity, price, amount, notes, and confidence directly before saving.
- Choose `Cloud AI first` or `Local fallback only` from the Record screen to make the AI route explicit during demos.
- Save the structured transaction to SQLite.
- See a “Saved just now” receipt with bookkeeping side effects.
- View the ledger, customer credit book, and inventory in a Gradio interface.
- Monitor business insights, an Insight Coach, a Command Center, a seller-day activity timeline, and a daily sales/expense chart.
- Use a mobile-first, business-style Gradio interface with custom styling.
- Run a Daily Closeout that prepares PDF, WhatsApp summary, and CSV exports together.
- Download a Daily Summary PDF report.
- Generate a WhatsApp-ready daily business summary.
- Generate customer follow-up reminders and an inventory reorder list.
- Capture field-test evidence with a seller checklist and anonymized feedback notes.
- Offload speech transcription and LLM parsing to optional Modal endpoints.
- Edit or delete saved transactions while keeping customer credit and inventory balances consistent.
- Export the ledger as CSV for spreadsheet sharing.

When Modal endpoints are configured, parsing runs through the Modal backend using `nvidia/NVIDIA-Nemotron-3-Nano-4B` via Hugging Face Inference. If Modal is unavailable or returns an invalid response, VoiceLedger falls back to the local rule parser for demo reliability. The `Local fallback only` mode intentionally skips Modal for local-first demos and reliability checks.

VoiceLedger is designed for the Build Small Hackathon Backyard AI track: a concrete, real-world bookkeeping problem for informal sellers and home businesses. The demo story is anonymized around a local seller who tracks sales, customer dues, stock, and daily profit from short voice notes.

## Judge Demo Flow

Use the `Sections` navigation in the Space:

1. `Record Text & Voice`: click `Seed Demo Transactions`, then type or speak `Sold 12 mangoes, 20 each`.
2. Parse and inspect the review card; warning badges show missing fields, low confidence, duplicate risk, or negative stock.
3. Edit the inline review fields before saving to show correction UX for real sellers.
4. Toggle `Cloud AI first` versus `Local fallback only` to show the Modal/Nemotron path and deterministic backup.
5. Save the reviewed transaction and show the “Saved just now” receipt.
6. Open `Dashboard`, `Customer Credit`, `Inventory`, and `Ledger` to show the Insight Coach, timeline, details, and automatic bookkeeping updates.
7. Open `Field Test` to show the seller checklist and anonymized feedback notes.
8. Open `Reports & PDF` to run Daily Closeout, download the PDF/CSV, and generate the WhatsApp summary.
9. Open `Demo Health` to show Modal backend status, deployed backend version, NVIDIA Nemotron parser status, SQLite, PDF support, and configured endpoints.

## Example Inputs

Try these in `Record Text & Voice` or paste them together in `Bulk Import`. The Record page groups examples by English, Hinglish, Gujarati-lite, Spanish, French, and Portuguese so the local seller language story is visible in the UI.

```text
Sold 12 mangoes, 20 each
Paid 500 for supplies
Amit owes 100
Bought 50 mangoes
Amit ne 100 dene hai
50 mango kharida
Vendí 12 mangos, 20 cada uno
Vendu 12 mangues, 20 chacun
Vendi 12 mangas, 20 cada
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
| `Amit ne 100 dene hai` | Customer credit, customer `Amit`, amount `100` |
| `Amit ne 50 diya` | Customer payment, customer `Amit`, amount `50` |
| `50 mango kharida` | Inventory purchase, quantity `50`, item `mango` |
| `50 mango lidha` | Inventory purchase, quantity `50`, item `mango` |
| `Vendí 12 mangos, 20 cada uno` | Sale, quantity `12`, item `mangos`, unit price `20`, amount `240` |
| `Pagué 500 por suministros` | Expense, amount `500`, item `suministros` |
| `Amit debe 100` | Customer credit, customer `Amit`, amount `100` |
| `Vendu 12 mangues, 20 chacun` | Sale, quantity `12`, item `mangues`, unit price `20`, amount `240` |
| `Amit doit 100` | Customer credit, customer `Amit`, amount `100` |
| `Vendi 12 mangas, 20 cada` | Sale, quantity `12`, item `mangas`, unit price `20`, amount `240` |
| `Amit deve 100` | Customer credit, customer `Amit`, amount `100` |

## Demo Script

1. Use `Seller Setup` to show business name, currency, low-stock threshold, and language style.
2. Use the `Hackathon Demo Launchpad` on the first screen to seed demo transactions.
3. Open `Record Text & Voice`, speak or type `Sold 12 mangoes, 20 each`, parse it, and review the human-readable transaction card.
4. Correct one inline review field before saving, such as quantity or amount, to show the seller correction loop.
5. Show the parse status and warning badges: Modal/NVIDIA Nemotron when available, local fallback when needed.
6. Save the transaction and show the Command Center plus the receipt with stock, customer, or amount side effects.
7. Open `Dashboard`, `Customer Credit`, and `Inventory` to show the Insight Coach, timeline charts, customer detail, follow-up message, inventory detail, reorder list, and automatic bookkeeping updates.
8. Open `Field Test` to show what a seller tried and what changed after feedback.
9. Open `Ledger`, load a transaction by id, update or delete it, then show refreshed balances.
10. Run Daily Closeout from `Reports & PDF`, then download CSV/PDF and generate the WhatsApp summary.
11. Click `Check Demo Health` from the launchpad, or open `Demo Health`, to show Modal health, deployed backend version, Nemotron status, database, PDF, and endpoint checks.

## Screenshot and GIF Moments

Capture these three moments for the Space README, demo video, or social post:

- `Record Text & Voice`: Today’s Work quick actions, review card, warning badges, and save receipt.
- `Dashboard`: Insight Coach, metrics, seller-day activity timeline, sales/expense timeline, top-selling item, low-stock table, and outstanding credit.
- `Field Test`: seller checklist, anonymized “who/tried/changed” notes, and saved evidence status.
- `Reports & PDF` plus `Ledger`: Daily Closeout, PDF/WhatsApp export, CSV download, and ledger correction.
- `Submission Story`: AI pipeline strip and “Why small models fit” card for the Modal/Nemotron story.

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
- The Insight Coach turns those dashboard signals into next actions, such as credit follow-up, restocking, and daily closeout.
- Customer and inventory detail views show transaction history for one customer or item.
- Smart review warnings flag low confidence, missing fields, duplicate risk, and negative stock before save.
- Inline review editing lets sellers correct the parsed transaction before the save touches the ledger.
- Seller setup persists business name, currency label, low-stock threshold, and language style in SQLite.
- Field Test persists anonymized seller evidence and a workflow checklist in SQLite.
- Local fallback rules include common English, Hinglish, Hindi-lite, Gujarati-lite, Spanish, French, and Portuguese seller notes.
- Customer follow-up and inventory reorder helpers generate WhatsApp-ready action messages.
- WhatsApp summaries provide a short copyable daily recap for sharing.
- Bulk import splits pasted notes by line, parses each line, supports review edits, and saves all reviewed transactions.
- Modal integration lives in `backend/`; if endpoint URLs are not configured, local fallback stays active.
- The Record screen includes a local-only AI mode that skips Modal while preserving the same transaction review and save flow.
- NVIDIA Nemotron 3 Nano 4B is used by the Modal parser endpoint and is also available as a local `transformers` parser provider for strict JSON transaction extraction.
- The Demo Health section checks Modal reachability, deployed backend version, NVIDIA Nemotron parser status, SQLite availability, PDF support, and configured endpoint status.
- The Submission Story section shows the AI pipeline and explains why a constrained transaction schema is a strong small-model fit.
- Ledger edits and deletes rebuild customer balances and inventory from saved transactions to avoid stale side effects.
- CSV export downloads all ledger rows in the same column order as the app table.
- The UI uses a custom theme, responsive spacing, and dashboard cards instead of the default Gradio look.
