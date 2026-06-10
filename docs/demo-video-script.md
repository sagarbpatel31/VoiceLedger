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
- Structured output
- Parse source/status
- Save confirmation

## 0:45-1:05 — Bookkeeping Updates

Use the `Sections` navigation to open:

- `Dashboard` to show sales/profit/credit
- `Customer Credit` to show dues
- `Inventory` to show stock
- `Ledger` to show saved transactions

Say: “The model handles messy input, but the app owns the accounting state.”

## 1:05-1:20 — Correction and Export

In `Ledger`, load a transaction by id, update or delete it, and show balances refresh.

Click `Download CSV`.

Open `Reports & PDF`, generate the PDF and WhatsApp summary.

Suggested screenshot/GIF moments:

- Record flow: note input, structured output, parse source, save confirmation.
- Dashboard: sales, expenses, profit, credit, top item, low-stock inventory.
- Reports/Ledger: PDF download, WhatsApp summary, CSV export.

## 1:20-1:30 — Close

Close with:

“VoiceLedger turns everyday seller notes into a working ledger: voice, credit, stock, reports, and exports in one Gradio Space.”
