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

#voiceledger-app,
#voiceledger-app *,
#voiceledger-app .svelte-1ipelgc,
#voiceledger-app .svelte-1ipelgc *,
#voiceledger-app .prose,
#voiceledger-app .prose * {
  color: var(--vl-text) !important;
}

#voiceledger-app [disabled],
#voiceledger-app [aria-disabled="true"],
#voiceledger-app .disabled,
#voiceledger-app .generating,
#voiceledger-app .generating *,
#voiceledger-app .pending,
#voiceledger-app .pending *,
#voiceledger-app .loading,
#voiceledger-app .loading *,
#voiceledger-app .wrap,
#voiceledger-app .wrap *,
#voiceledger-app .block,
#voiceledger-app .block *,
#voiceledger-app .form,
#voiceledger-app .form *,
#voiceledger-app .output-class,
#voiceledger-app .output-class *,
#voiceledger-app .empty,
#voiceledger-app .empty * {
  opacity: 1 !important;
}

#voiceledger-app h1,
#voiceledger-app h2,
#voiceledger-app h3,
#voiceledger-app h4,
#voiceledger-app h5,
#voiceledger-app h6,
#voiceledger-app p,
#voiceledger-app span,
#voiceledger-app label,
#voiceledger-app legend,
#voiceledger-app .label-wrap,
#voiceledger-app .prose,
#voiceledger-app .prose * {
  color: var(--vl-text) !important;
}

#voiceledger-app .vl-hero,
#voiceledger-app .vl-hero * {
  color: #ffffff !important;
}

#voiceledger-app code {
  background: #2c2926 !important;
  border-radius: 6px !important;
  color: #ffffff !important;
  padding: 2px 6px !important;
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

.vl-app-nav {
  background: #ffffff !important;
  border: 1px solid var(--vl-border) !important;
  border-radius: 14px !important;
  box-shadow: 0 10px 24px rgba(31, 42, 31, 0.05) !important;
  color: var(--vl-text) !important;
  margin: 0 0 12px !important;
  opacity: 1 !important;
  padding: 10px !important;
}

.vl-app-nav,
.vl-app-nav * {
  color: var(--vl-text) !important;
  opacity: 1 !important;
}

.vl-app-nav strong {
  display: block !important;
  font-size: 13px !important;
  font-weight: 800 !important;
  margin: 0 0 8px !important;
  text-transform: uppercase !important;
}

.vl-app-nav div {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 8px !important;
}

.vl-app-nav a,
.vl-app-nav button {
  appearance: none !important;
  background: #eef6ed !important;
  border: 1px solid #b9d4b4 !important;
  border-radius: 999px !important;
  color: #183525 !important;
  cursor: pointer !important;
  display: inline-flex !important;
  font-size: 14px !important;
  font-weight: 800 !important;
  justify-content: center !important;
  line-height: 1 !important;
  min-height: 36px !important;
  padding: 8px 12px !important;
  text-decoration: none !important;
  white-space: nowrap !important;
}

.vl-app-nav a:hover,
.vl-app-nav button:hover {
  background: var(--vl-accent) !important;
  border-color: var(--vl-accent) !important;
  color: #ffffff !important;
}

.vl-app-nav button,
.vl-app-nav button * {
  color: #183525 !important;
  opacity: 1 !important;
}

.vl-app-nav button:hover,
.vl-app-nav button:hover * {
  color: #ffffff !important;
}

.vl-page-anchor {
  display: block !important;
  scroll-margin-top: 14px !important;
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

.vl-info-panel {
  background: #ffffff !important;
  border: 1px solid var(--vl-border) !important;
  border-radius: 12px !important;
  box-shadow: 0 8px 20px rgba(31, 42, 31, 0.04) !important;
  color: var(--vl-text) !important;
  margin: 0 !important;
  opacity: 1 !important;
  padding: 12px 14px !important;
}

.vl-info-panel,
.vl-info-panel * {
  color: var(--vl-text) !important;
  opacity: 1 !important;
}

.vl-info-panel h2,
.vl-section-heading {
  color: var(--vl-text) !important;
  font-size: 18px !important;
  font-weight: 800 !important;
  letter-spacing: 0 !important;
  line-height: 1.25 !important;
  margin: 0 0 4px !important;
}

.vl-info-panel p {
  color: var(--vl-text) !important;
  font-size: 15px !important;
  line-height: 1.45 !important;
  margin: 4px 0 !important;
}

.vl-judge-panel {
  background: #ffffff !important;
  border: 1px solid var(--vl-border) !important;
  border-radius: 14px !important;
  box-shadow: var(--vl-shadow) !important;
  color: var(--vl-text) !important;
  padding: 14px !important;
}

.vl-judge-panel,
.vl-judge-panel * {
  color: var(--vl-text) !important;
  opacity: 1 !important;
}

.vl-judge-panel h2 {
  font-size: 18px !important;
  font-weight: 800 !important;
  margin: 0 0 10px !important;
}

.vl-judge-panel ol {
  display: grid !important;
  gap: 10px !important;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)) !important;
  list-style: none !important;
  margin: 0 !important;
  padding: 0 !important;
}

.vl-judge-panel li {
  background: #f6f7f2 !important;
  border: 1px solid var(--vl-border) !important;
  border-radius: 10px !important;
  padding: 10px !important;
}

.vl-judge-panel li strong {
  display: block !important;
  font-size: 14px !important;
  font-weight: 800 !important;
}

.vl-judge-panel li span {
  color: #475247 !important;
  display: block !important;
  font-size: 13px !important;
  line-height: 1.35 !important;
  margin-top: 4px !important;
}

.vl-health-line {
  background: #eef6ed !important;
  border: 1px solid #b9d4b4 !important;
  border-radius: 10px !important;
  color: #183525 !important;
  font-size: 14px !important;
  font-weight: 800 !important;
  line-height: 1.35 !important;
  margin: 12px 0 0 !important;
  padding: 10px !important;
}

.vl-today-panel,
.vl-review-card,
.vl-receipt-card,
.vl-detail-card,
.vl-closeout-card {
  background: #ffffff !important;
  border: 1px solid var(--vl-border) !important;
  border-radius: 14px !important;
  box-shadow: var(--vl-shadow) !important;
  color: var(--vl-text) !important;
  padding: 14px !important;
}

.vl-today-panel *,
.vl-review-card *,
.vl-receipt-card *,
.vl-detail-card *,
.vl-closeout-card * {
  color: var(--vl-text) !important;
  opacity: 1 !important;
}

.vl-today-panel h2,
.vl-review-card h2,
.vl-receipt-card h2,
.vl-detail-card h2,
.vl-closeout-card h2 {
  font-size: 18px !important;
  font-weight: 800 !important;
  margin: 0 0 10px !important;
}

.vl-today-panel div,
.vl-review-grid,
.vl-closeout-grid {
  display: grid !important;
  gap: 10px !important;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)) !important;
}

.vl-today-panel span,
.vl-review-grid div,
.vl-closeout-grid span {
  background: #f6f7f2 !important;
  border: 1px solid var(--vl-border) !important;
  border-radius: 10px !important;
  display: block !important;
  padding: 10px !important;
}

.vl-today-panel strong,
.vl-review-grid span,
.vl-closeout-grid strong {
  color: #475247 !important;
  display: block !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  text-transform: uppercase !important;
}

.vl-review-grid strong,
.vl-closeout-grid span {
  font-size: 16px !important;
  font-weight: 800 !important;
  margin-top: 4px !important;
}

.vl-review-header p,
.vl-receipt-card p,
.vl-detail-card p,
.vl-closeout-card p {
  color: #475247 !important;
  font-size: 14px !important;
  line-height: 1.4 !important;
  margin: 4px 0 0 !important;
}

.vl-warning-row {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 8px !important;
  margin-top: 12px !important;
}

.vl-warning-badge,
.vl-success-badge {
  border-radius: 999px !important;
  display: inline-block !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  padding: 6px 10px !important;
}

.vl-warning-badge {
  background: #fff3cd !important;
  border: 1px solid #e3bc5b !important;
  color: #5f370e !important;
}

.vl-success-badge {
  background: #e7f6ed !important;
  border: 1px solid #9bd2ad !important;
  color: #145a39 !important;
}

.vl-receipt-card {
  border-color: #9bd2ad !important;
}

.vl-chip {
  background: #2c2926 !important;
  border-radius: 6px !important;
  color: #ffffff !important;
  display: inline-block !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
  font-size: 13px !important;
  margin: 2px 4px 2px 0 !important;
  padding: 3px 7px !important;
  white-space: nowrap !important;
}

.vl-section-heading {
  margin-top: 10px !important;
}

.vl-muted,
.vl-muted p {
  color: var(--vl-muted) !important;
}

.vl-metric-card {
  background: var(--vl-surface) !important;
  border: 1px solid var(--vl-border) !important;
  border-radius: 14px;
  box-shadow: var(--vl-shadow) !important;
  color: var(--vl-text) !important;
  min-height: 112px;
  opacity: 1 !important;
  padding: 16px;
}

.vl-metric-card,
.vl-metric-card * {
  opacity: 1 !important;
}

.vl-metric-label {
  color: #475247 !important;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  opacity: 1 !important;
  text-transform: uppercase;
}

.vl-metric-value {
  color: var(--vl-text) !important;
  font-size: 30px;
  font-weight: 800;
  line-height: 1.1;
  margin-top: 10px;
  opacity: 1 !important;
}

.vl-metric-note {
  color: #475247 !important;
  font-size: 12px;
  margin-top: 8px;
  opacity: 1 !important;
}

.vl-profit-positive .vl-metric-value {
  color: var(--vl-accent) !important;
}

.vl-profit-negative .vl-metric-value {
  color: #b42318 !important;
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
  color: #ffffff !important;
}

#voiceledger-app button.primary *,
#voiceledger-app .primary * {
  color: #ffffff !important;
}

#voiceledger-app button.primary:hover,
#voiceledger-app .primary:hover {
  background: var(--vl-accent-strong) !important;
  border-color: var(--vl-accent-strong) !important;
  color: #ffffff !important;
}

.vl-copy-button {
  background: var(--vl-text);
  border: 1px solid var(--vl-text);
  border-radius: 10px;
  color: #ffffff !important;
  cursor: pointer;
  font-weight: 700;
  margin-top: 8px;
  min-height: 42px;
  padding: 0 16px;
}

.vl-copy-button:hover {
  background: #334033;
}

.vl-example-row {
  gap: 8px !important;
}

.vl-example-row button,
#voiceledger-app button.secondary {
  background: var(--vl-surface) !important;
  border: 1px solid var(--vl-border) !important;
  color: var(--vl-text) !important;
}

.vl-example-row button:hover,
#voiceledger-app button.secondary:hover {
  border-color: var(--vl-accent) !important;
  color: var(--vl-accent-strong) !important;
}

#voiceledger-app textarea,
#voiceledger-app input,
#voiceledger-app select {
  border-radius: 12px !important;
  color: var(--vl-text) !important;
}

#voiceledger-app textarea,
#voiceledger-app input,
#voiceledger-app select {
  background: #ffffff !important;
  border-color: var(--vl-border) !important;
}

#voiceledger-app .wrap {
  border-radius: 12px !important;
  color: var(--vl-text) !important;
}

#voiceledger-app .wrap,
#voiceledger-app .wrap *,
#voiceledger-app .label-wrap,
#voiceledger-app .label-wrap *,
#voiceledger-app label,
#voiceledger-app label *,
#voiceledger-app legend,
#voiceledger-app legend *,
#voiceledger-app .block-label,
#voiceledger-app .block-label * {
  color: var(--vl-text) !important;
  opacity: 1 !important;
}

#voiceledger-app textarea::placeholder,
#voiceledger-app input::placeholder {
  color: #6d756b !important;
  opacity: 1 !important;
}

#voiceledger-app .tab-nav {
  display: none !important;
  height: 0 !important;
  margin: 0 !important;
  opacity: 0 !important;
  overflow: hidden !important;
  padding: 0 !important;
  pointer-events: none !important;
  visibility: hidden !important;
}

#voiceledger-app .tab-nav *,
#voiceledger-app .tab-nav button {
  display: none !important;
  opacity: 0 !important;
  visibility: hidden !important;
}

#voiceledger-app .tab-nav button *,
#voiceledger-app [role="tab"] * {
  color: inherit !important;
  opacity: 1 !important;
  visibility: visible !important;
}

#voiceledger-app .tab-nav button.selected {
  background: var(--vl-text) !important;
  color: #ffffff !important;
}

#voiceledger-app [role="tablist"] {
  display: none !important;
  height: 0 !important;
  margin: 0 !important;
  opacity: 0 !important;
  overflow: hidden !important;
  padding: 0 !important;
  pointer-events: none !important;
  visibility: hidden !important;
}

#voiceledger-app [role="tabpanel"] {
  display: block !important;
  height: auto !important;
  opacity: 1 !important;
  overflow: visible !important;
  visibility: visible !important;
}

#voiceledger-app [role="tabpanel"][hidden],
#voiceledger-app [role="tabpanel"][aria-hidden="true"] {
  display: block !important;
  height: auto !important;
  opacity: 1 !important;
  visibility: visible !important;
}

#voiceledger-app [role="tab"] {
  display: none !important;
  opacity: 0 !important;
  visibility: hidden !important;
}

#voiceledger-app [role="tab"][aria-selected="true"] {
  background: #eef6ed !important;
  color: var(--vl-accent) !important;
}

#voiceledger-app table {
  background: #ffffff !important;
  border-radius: 12px !important;
  color: var(--vl-text) !important;
  overflow: hidden !important;
}

#voiceledger-app table *,
#voiceledger-app td *,
#voiceledger-app th *,
#voiceledger-app .dataframe td *,
#voiceledger-app [data-testid="dataframe"] td * {
  opacity: 1 !important;
}

#voiceledger-app th {
  background: #1f2a1f !important;
  color: #ffffff !important;
  font-weight: 800 !important;
}

#voiceledger-app td {
  background: #ffffff !important;
  color: var(--vl-text) !important;
}

#voiceledger-app .dataframe,
#voiceledger-app .dataframe *,
#voiceledger-app [data-testid="dataframe"],
#voiceledger-app [data-testid="dataframe"] * {
  color: var(--vl-text) !important;
  opacity: 1 !important;
}

#voiceledger-app [data-testid="dataframe"] th,
#voiceledger-app [data-testid="dataframe"] th *,
#voiceledger-app .dataframe th,
#voiceledger-app .dataframe th * {
  background: #1f2a1f !important;
  color: #ffffff !important;
  font-weight: 800 !important;
}

.vl-status,
.vl-status p,
.vl-status h1,
.vl-status h2,
.vl-status h3,
.vl-status h4,
.vl-status h5,
.vl-status h6,
.vl-status strong,
.vl-status span {
  color: var(--vl-text) !important;
  margin: 0 !important;
  opacity: 1 !important;
}

.vl-status {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--vl-border);
  border-radius: 12px;
  padding: 10px 12px !important;
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
