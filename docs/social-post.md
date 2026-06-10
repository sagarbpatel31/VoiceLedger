# VoiceLedger Social Post Draft

Built VoiceLedger for the Hugging Face Build Small Hackathon.

It is a voice-first bookkeeping app for informal sellers, street vendors, home businesses, and small shop owners who need a ledger without opening a spreadsheet.

Examples:

- “Sold 12 mangoes, 20 each”
- “Paid 500 for supplies”
- “Amit owes 100”
- “Bought 50 mangoes”

VoiceLedger turns those notes into a working ledger with:

- speech-to-text
- NVIDIA Nemotron transaction parsing through Modal
- local rule fallback for reliability
- SQLite ledger
- customer credit tracking
- inventory tracking
- dashboard insights
- PDF, CSV, and WhatsApp summaries

For judges: the demo flow is seed data -> record/type -> parse/save -> dashboard/reports. The Space shows Modal health, Nemotron status, SQLite, PDF support, and endpoint configuration.

The goal is practical AI for a real everyday workflow: helping small sellers track money, dues, and stock without spreadsheets.

Space: https://huggingface.co/spaces/sagarp22/VoiceLedger

#BuildSmall #HuggingFace #Gradio #Modal #NVIDIA #SmallModels #AI
