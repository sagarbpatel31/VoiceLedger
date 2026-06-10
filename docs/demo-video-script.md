# VoiceLedger Demo Video Script

Target length: 60-90 seconds.

## 0:00-0:10 — Problem

VoiceLedger is a voice-first bookkeeping app for informal sellers and home businesses. The target user records quick notes like “Sold 12 mangoes, 20 each” or “Amit owes 100” while working.

## 0:10-0:25 — Seed and Health

On the first screen, use `Hackathon Demo Launchpad` and click `Seed Demo Transactions`. If the tab bar is fully visible, the same control is also available in the `Submission Story` tab.

Click `Check Demo Health` from the launchpad, or open `Demo Health`, and show:

- Modal backend status
- Deployed backend version
- SQLite database
- PDF support
- Configured Modal endpoints

Say: “The Space calls Modal first for speech and NVIDIA Nemotron parsing, with local fallback for reliability.”

## 0:25-0:45 — Voice or Text Transaction

Open `Record Text & Voice`.

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

Open:

- `Dashboard` to show sales/profit/credit
- `Customer Credit` to show dues
- `Inventory` to show stock
- `Ledger` to show saved transactions

Say: “The model handles messy input, but the app owns the accounting state.”

## 1:05-1:20 — Correction and Export

In `Ledger`, load a transaction by id, update or delete it, and show balances refresh.

Click `Download CSV`.

Open `Reports & PDF`, generate the PDF and WhatsApp summary.

## 1:20-1:30 — Close

Close with:

“VoiceLedger turns everyday seller notes into a working ledger: voice, credit, stock, reports, and exports in one Gradio Space.”
