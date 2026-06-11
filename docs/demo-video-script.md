# VoiceLedger Demo Video Script

Target length: 60-90 seconds.

## 0:00-0:10 — Problem

VoiceLedger is a voice-first bookkeeping app for informal sellers and home businesses. The target user records quick notes like “Sold 12 mangoes, 20 each” or “Amit owes 100” while working.

## 0:10-0:25 — Judge Flow and Health

On the first screen, show the `Judge Demo Flow` panel:

```text
1. Seed demo data -> 2. Record/type -> 3. Save -> 4. View dashboard/reports
```

Click `Seed Demo Transactions`.

Show `Seller Setup` and mention that business name, currency, low-stock threshold, and language style are saved in SQLite.

Show the first-run guide and multilingual examples so judges see English, Hinglish, Gujarati-lite, Spanish, French, and Portuguese seller notes.

Open `Submission Story` and show the AI pipeline strip plus the “Why small models fit” card.

Click `Check Demo Health` from the launchpad, or open `Demo Health`, and show:

- Modal backend status
- Deployed backend version
- NVIDIA Nemotron parser
- SQLite database
- PDF support
- Configured Modal endpoints

Say: “The Space calls Modal first for speech and NVIDIA Nemotron parsing, with local fallback for reliability.”

## 0:25-0:45 — Voice or Text Transaction

Use the `Sections` navigation to open `Record Text & Voice`.

Type or speak:

```text
Sold 12 mangoes, 20 each
```

Click parse. Show:

- Transcript if using voice
- Human-friendly transaction review card
- Inline review fields for correcting item, quantity, amount, customer, and notes before saving
- Warning badges for low confidence, missing fields, duplicate risk, or negative stock when present
- Parse source/status
- Command Center update
- “Saved just now” receipt with stock, customer, or amount side effects

## 0:45-1:05 — Bookkeeping Updates

Use the `Sections` navigation to open:

- `Dashboard` to show sales/profit/credit and the sales/expense timeline
- `Field Test` to show the seller checklist and anonymized “who/tried/changed” notes
- `Customer Credit` to show dues, a selected customer detail view, and a follow-up message
- `Inventory` to show stock, a selected item detail view, and the reorder list
- `Ledger` to show saved transactions

Say: “The model handles messy input, but the app owns the accounting state.”

## 1:05-1:20 — Correction and Export

In `Ledger`, load a transaction by id, update or delete it, and show balances refresh.

Click `Download CSV`.

Open `Reports & PDF`, run `Daily Closeout`, then generate the PDF, WhatsApp summary, and CSV export.

Suggested screenshot/GIF moments:

- Record flow: first-run guide, multilingual examples, review card, inline correction, parse source, warning badges, save receipt.
- Seller setup: currency/threshold/language style and Command Center.
- Field Test: seller checklist and feedback notes.
- Submission Story: AI pipeline and small-model fit card.
- Dashboard: sales, expenses, profit, credit, timeline, top item, low-stock inventory.
- Reports/Ledger: Daily Closeout, PDF download, WhatsApp summary, CSV export.

## 1:20-1:30 — Close

Close with:

“VoiceLedger turns everyday seller notes into a working ledger: voice, credit, stock, reports, and exports in one Gradio Space.”
