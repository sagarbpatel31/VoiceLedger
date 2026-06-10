# VoiceLedger Field Notes

## Problem

VoiceLedger is built for an informal seller who records business activity in short spoken notes instead of spreadsheets. The recurring jobs are simple but easy to lose track of during a busy day: sales, expenses, customer dues, payments, and stock.

The anonymized target user is a local seller who needs to answer practical questions quickly:

- What did I sell today?
- Who still owes me money?
- How much stock do I have left?
- Did I make a profit today?
- Can I share a short summary without opening a spreadsheet?

## Small-Model Fit

The app intentionally keeps the bookkeeping workflow narrow. Voice and messy text are converted into a small transaction schema, then deterministic ledger code handles balances, inventory, reports, and exports.

NVIDIA Nemotron is used through the Modal backend for transaction parsing when available. The local rule parser remains the fallback so the app stays reliable during a live demo or on a basic Hugging Face Space.

This is a good small-model problem because the output space is constrained: a transaction type, item, quantity, price, amount, customer, payment status, notes, and confidence. The model does not need to run a general accounting system; it only has to normalize everyday seller notes into structured records.

## System Shape

- Gradio Space for the product UI.
- SQLite for local ledger persistence.
- faster-whisper for speech-to-text.
- Modal endpoint for speech and Nemotron parsing.
- Rule parser fallback for deterministic demo safety.
- Customer and inventory tables are derived from saved transactions and rebuilt after edits/deletes.

## Demo Flow

1. Seed demo transactions from the Submission Story tab.
2. Record or type: `Sold 12 mangoes, 20 each`.
3. Show the parse source: Modal/Nemotron or local fallback.
4. Save the transaction.
5. Show Dashboard totals, Ledger row, Customer Credit, and Inventory.
6. Edit or delete a transaction and show balances rebuilding.
7. Export CSV, PDF report, and WhatsApp daily summary.
8. Open Demo Health to show Modal, backend version, SQLite, PDF, and endpoint checks.

## What We Learned

The strongest product behavior is not the model call itself. It is the reliable loop around it: voice input, structured review, save, correction, and export. Informal sellers need speed, but they also need a way to fix mistakes. Edit/delete and CSV export make the app credible as a bookkeeping tool instead of a parser demo.

The small-model constraint helped keep the app honest. The model handles the fuzzy human input; the code owns the accounting state.
