# VoiceLedger Submission Checklist

## Required Submission Items

- Hugging Face Space is public and running.
- README explains the problem, target user, model flow, and demo path.
- Demo video is recorded and attached/shared.
- Social post is published with the Space link.
- Submission form includes the Space URL.

## Demo Verification

- `Demo Health` shows Modal reachable and backend version.
- Text parse works with `Sold 12 mangoes, 20 each`.
- Voice parse works and transcript appears.
- Save updates Dashboard and Ledger.
- Customer Credit tab reflects `Amit owes 100` and `Amit paid 40`.
- Inventory reflects purchases and sales.
- Ledger edit/delete works and derived balances rebuild.
- CSV export downloads from Ledger.
- PDF report downloads from Reports.
- WhatsApp summary generates copyable text.

## Prize Alignment

- Backyard AI: specific informal seller bookkeeping problem.
- Best Demo: voice-to-ledger flow, dashboard, reports, exports.
- NVIDIA Nemotron Quest: Nemotron parser endpoint through Modal.
- Modal Awards: Modal backend for speech and parsing endpoints.
- Off-Brand Award: practical AI for street vendors and home businesses.
- Field Notes: `docs/field-notes.md`.

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
