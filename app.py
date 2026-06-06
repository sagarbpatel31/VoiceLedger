"""Hugging Face Spaces entrypoint for VoiceLedger."""

from voiceledger.ui.gradio_app import create_app
from voiceledger.ui.theme import APP_CSS, create_theme


demo = create_app()


if __name__ == "__main__":
    demo.launch(theme=create_theme(), css=APP_CSS)
