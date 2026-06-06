"""Custom Gradio theme and CSS for VoiceLedger."""

from __future__ import annotations

import gradio as gr


APP_CSS = """
:root {
  --vl-bg: #f6f7f2;
  --vl-surface: #ffffff;
  --vl-surface-strong: #f0f3ea;
  --vl-border: #d9dfcf;
  --vl-text: #1f2a1f;
  --vl-muted: #637064;
  --vl-accent: #1f7a4d;
  --vl-accent-strong: #145a39;
  --vl-warn: #9a5b14;
  --vl-danger-bg: #fff3cd;
  --vl-shadow: 0 16px 36px rgba(31, 42, 31, 0.08);
}

body,
.gradio-container {
  background: var(--vl-bg) !important;
  color: var(--vl-text) !important;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}

#voiceledger-app {
  max-width: 1180px !important;
  margin: 0 auto !important;
  padding: 14px !important;
}

#voiceledger-app .contain {
  gap: 14px !important;
}

.vl-hero {
  background: linear-gradient(135deg, #163d2b 0%, #1f7a4d 55%, #d7b56d 100%);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 18px;
  box-shadow: var(--vl-shadow);
  color: #ffffff;
  margin-bottom: 12px;
  overflow: hidden;
  padding: 22px 18px;
}

.vl-hero h1 {
  color: #ffffff !important;
  font-size: 32px !important;
  line-height: 1.05 !important;
  margin: 0 !important;
}

.vl-hero p {
  color: rgba(255, 255, 255, 0.88) !important;
  font-size: 15px !important;
  margin: 8px 0 0 !important;
}

.vl-panel,
.vl-panel > div {
  background: var(--vl-surface) !important;
  border: 1px solid var(--vl-border) !important;
  border-radius: 14px !important;
  box-shadow: var(--vl-shadow) !important;
}

.vl-panel {
  padding: 14px !important;
}

.vl-section-title h3,
.vl-section-title h2 {
  color: var(--vl-text) !important;
  letter-spacing: 0 !important;
  margin-bottom: 4px !important;
}

.vl-muted,
.vl-muted p {
  color: var(--vl-muted) !important;
}

.vl-metric-card {
  background: var(--vl-surface);
  border: 1px solid var(--vl-border);
  border-radius: 14px;
  box-shadow: var(--vl-shadow);
  min-height: 112px;
  padding: 16px;
}

.vl-metric-label {
  color: var(--vl-muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.vl-metric-value {
  color: var(--vl-text);
  font-size: 30px;
  font-weight: 800;
  line-height: 1.1;
  margin-top: 10px;
}

.vl-metric-note {
  color: var(--vl-muted);
  font-size: 12px;
  margin-top: 8px;
}

.vl-profit-positive .vl-metric-value {
  color: var(--vl-accent);
}

.vl-profit-negative .vl-metric-value {
  color: #b42318;
}

#voiceledger-app button {
  border-radius: 10px !important;
  font-weight: 700 !important;
  min-height: 42px !important;
}

#voiceledger-app button.primary,
#voiceledger-app .primary {
  background: var(--vl-accent) !important;
  border-color: var(--vl-accent) !important;
}

#voiceledger-app button.primary:hover,
#voiceledger-app .primary:hover {
  background: var(--vl-accent-strong) !important;
  border-color: var(--vl-accent-strong) !important;
}

#voiceledger-app textarea,
#voiceledger-app input,
#voiceledger-app .wrap {
  border-radius: 12px !important;
}

#voiceledger-app .tab-nav {
  background: rgba(255, 255, 255, 0.78) !important;
  border: 1px solid var(--vl-border) !important;
  border-radius: 14px !important;
  box-shadow: 0 10px 24px rgba(31, 42, 31, 0.05);
  gap: 4px !important;
  overflow-x: auto !important;
  padding: 6px !important;
}

#voiceledger-app .tab-nav button {
  border-radius: 10px !important;
  color: var(--vl-muted) !important;
  font-size: 14px !important;
  white-space: nowrap !important;
}

#voiceledger-app .tab-nav button.selected {
  background: var(--vl-text) !important;
  color: #ffffff !important;
}

#voiceledger-app table {
  border-radius: 12px !important;
  overflow: hidden !important;
}

#voiceledger-app th {
  background: var(--vl-surface-strong) !important;
  color: var(--vl-text) !important;
  font-weight: 800 !important;
}

.vl-status,
.vl-status p {
  color: var(--vl-muted) !important;
  font-size: 14px !important;
  margin: 0 !important;
}

@media (min-width: 760px) {
  #voiceledger-app {
    padding: 24px !important;
  }

  .vl-hero {
    padding: 28px 28px;
  }

  .vl-hero h1 {
    font-size: 42px !important;
  }
}

@media (max-width: 759px) {
  #voiceledger-app {
    padding: 10px !important;
  }

  .vl-hero {
    border-radius: 14px;
    padding: 18px 14px;
  }

  .vl-hero h1 {
    font-size: 28px !important;
  }

  .vl-metric-card {
    min-height: 96px;
    padding: 14px;
  }

  .vl-metric-value {
    font-size: 26px;
  }
}
"""


def create_theme() -> gr.Theme:
    """Return the custom VoiceLedger Gradio theme."""
    return gr.themes.Soft(
        primary_hue="green",
        secondary_hue="stone",
        neutral_hue="stone",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    ).set(
        body_background_fill="#f6f7f2",
        block_background_fill="#ffffff",
        block_border_color="#d9dfcf",
        block_radius="14px",
        button_primary_background_fill="#1f7a4d",
        button_primary_background_fill_hover="#145a39",
        button_primary_text_color="#ffffff",
        input_background_fill="#ffffff",
    )
