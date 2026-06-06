"""Hugging Face Spaces entrypoint for VoiceLedger."""

from voiceledger.ui.gradio_app import create_app


demo = create_app()


if __name__ == "__main__":
    demo.launch()
