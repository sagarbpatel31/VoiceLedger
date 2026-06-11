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
- human-friendly review cards and smart warning badges
- save receipts that explain stock, credit, and amount side effects
- seller setup for currency, stock threshold, and language style
- English/Hinglish/Hindi-lite/Gujarati-lite/Spanish/French/Portuguese local fallback examples
- SQLite ledger
- customer credit tracking
- inventory tracking
- dashboard insights with a daily timeline
- customer and inventory detail drilldowns
- customer follow-up and inventory reorder messages
- PDF, CSV, and WhatsApp summaries
- one-click Daily Closeout
- a visible AI pipeline and small-model fit explanation for judges

For judges: the demo flow is seed data -> record/type -> review warnings -> save receipt -> dashboard/reports. The Space shows Modal health, Nemotron status, SQLite, PDF support, and endpoint configuration.

The goal is practical AI for a real everyday workflow: helping small sellers track money, dues, and stock without spreadsheets.

Space: https://huggingface.co/spaces/sagarp22/VoiceLedger

#BuildSmall #HuggingFace #Gradio #Modal #NVIDIA #SmallModels #AI
