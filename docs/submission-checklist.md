# VoiceLedger Submission Checklist

## Required Submission Items

- Hugging Face Space is public and running.
- README explains the problem, target user, model flow, Judge Demo Flow, and demo path.
- Demo video is recorded and attached/shared.
- Social post is published with the Space link.
- Submission form includes the Space URL.

## Demo Verification

- `Sections` navigation opens the correct page and no old Gradio tab row is visible.
- First screen shows `1. Seed demo data -> 2. Record/type -> 3. Save -> 4. View dashboard/reports`.
- `Submission Story` shows the AI pipeline strip.
- `Submission Story` shows the “Why small models fit” card.
- `Demo Health` shows Modal reachable and backend version.
- `Demo Health` shows NVIDIA Nemotron parser status.
- Seller Setup saves business name, currency label, low-stock threshold, and language style.
- Currency preset updates the currency label for INR, USD, EUR, GBP, MXN, and BRL.
- Text parse works with `Sold 12 mangoes, 20 each`.
- Local fallback parses `Amit ne 100 dene hai`, `Amit ne 50 diya`, and `50 mango kharida`.
- Voice parse works and transcript appears.
- Review card shows type, item, quantity, price, amount, customer, source, and confidence.
- Parse status shows source plus language/confidence.
- Smart warnings appear for low confidence, missing fields, duplicate risk, and negative stock.
- Save shows a receipt with transaction type, amount, and side effects.
- Command Center updates after save and seed.
- Voice command shortcuts work for `close today`, `show Amit`, and `stock mangoes`.
- Save updates Dashboard and Ledger.
- Dashboard timeline loads from saved transactions.
- Seller-day timeline shows recent saved transactions.
- Customer Credit section reflects `Amit owes 100` and `Amit paid 40`.
- Customer detail lookup shows customer transaction history and status.
- Customer follow-up generates a WhatsApp reminder.
- Inventory reflects purchases and sales.
- Inventory detail lookup shows bought, sold, current stock, and low-stock status.
- Inventory reorder list uses the configured threshold.
- Ledger edit/delete works and derived balances rebuild.
- CSV export downloads from Ledger.
- Daily Closeout generates PDF, CSV, WhatsApp summary, and a status line.
- PDF report downloads from Reports.
- WhatsApp summary generates copyable text in English, Spanish, French, and Portuguese.
- Field Test correction log shows edited review fields.

## Prize Alignment

- Backyard AI: specific informal seller bookkeeping problem.
- Best Demo: Today’s Work quick actions, review card, warnings, receipt, dashboard, reports, exports.
- NVIDIA Nemotron Quest: Nemotron parser endpoint through Modal.
- Modal Awards: Modal backend for speech and parsing endpoints.
- Off-Brand Award: custom mobile-first Gradio UI beyond the default look.
- Field Notes: `docs/field-notes.md`.

## Capture Assets

- Screenshot or GIF: Record flow with review card, parse source, warning badges, and save receipt.
- Screenshot or GIF: Submission Story with AI pipeline and small-model explanation.
- Screenshot or GIF: Dashboard with seeded transactions and timeline.
- Screenshot or GIF: Daily Closeout plus PDF, WhatsApp, and CSV exports.

## Final Manual Checks

Run locally:

```bash
env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest
```

Check Modal:

```bash
curl https://sagarpat3199--voiceledger-api.modal.run/health
curl https://sagarpat3199--voiceledger-api.modal.run/version
curl -X POST https://sagarpat3199--voiceledger-api.modal.run/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"Sold 12 mangoes, 20 each"}'
```
