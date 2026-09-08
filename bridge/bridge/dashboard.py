"""Dashboard HTML generation."""
from __future__ import annotations


def get_html() -> str:
    """Return the full dashboard HTML page."""
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Syx LLM Overlord</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Inter:wght@300;400;600&display=swap');

  :root {
    --bg-dark: #0a0a0f;
    --bg-panel: #12121a;
    --bg-card: #1a1a28;
    --border: #2a2a3a;
    --text: #c8c8d0;
    --text-dim: #666680;
    --text-bright: #e8e8f0;
    --gold: #d4a843;
    --gold-dim: #8a6b20;
    --red: #c44040;
    --green: #40a040;
    --blue: #4080c0;
    --purple: #8060c0;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--bg-dark);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    overflow: hidden;
    height: 100vh;
  }

  header {
    background: linear-gradient(180deg, #18182a 0%, var(--bg-dark) 100%);
    border-bottom: 1px solid var(--border);
    padding: 10px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 20px;
    min-width: 0;
  }

  .main-tabs {
    display: flex;
    gap: 4px;
  }

  .main-tab {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-dim);
    padding: 5px 14px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    font-family: 'Cinzel', serif;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    transition: all 0.2s;
  }

  .main-tab:hover {
    border-color: var(--gold-dim);
    color: var(--text);
  }

  .main-tab.active {
    border-color: var(--gold);
    color: var(--gold);
    background: var(--bg-card);
  }

  .app-shell {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 50px);
    min-height: 0;
    overflow: hidden;
  }

  .view {
    display: none;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .view-play.active {
    display: flex;
    flex-direction: column;
  }

  .view-map.active {
    display: flex;
    flex-direction: column;
    padding: 10px 14px;
    gap: 10px;
    min-height: 0;
  }

  .map-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    flex-shrink: 0;
  }

  .map-toolbar label {
    font-size: 11px;
    color: var(--text-dim);
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .map-toolbar select, .map-toolbar input[type=range] {
    background: var(--bg-dark);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
  }

  .map-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 10px;
    color: var(--text-dim);
  }

  .map-legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .map-legend-swatch {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid rgba(255,255,255,0.15);
  }

  .map-layout {
    display: flex;
    flex: 1;
    min-height: 0;
    gap: 12px;
  }

  .map-scroll-wrap {
    flex: 1;
    min-width: 0;
    min-height: 420px;
    overflow: auto;
    background: #0a0c0f;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .map-grid {
    display: grid;
    gap: 0;
    width: max-content;
    margin: 0 auto;
    user-select: none;
  }

  .map-cell {
    box-sizing: border-box;
    border: 1px solid rgba(255,255,255,0.04);
    cursor: crosshair;
    position: relative;
    font-size: 0;
    transition: outline 0.1s;
  }

  .map-cell:hover {
    outline: 2px solid var(--gold-dim);
    z-index: 2;
  }

  .map-cell.has-pin::after {
    content: '';
    position: absolute;
    inset: 2px;
    border: 2px solid var(--pin-color, #e91e63);
    border-radius: 2px;
    box-shadow: 0 0 6px var(--pin-color, #e91e63);
    pointer-events: none;
  }

  .map-cell.is-throne {
    outline: 2px solid #ffd700;
    z-index: 1;
  }

  .map-sidebar {
    width: 240px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
  }

  .map-pin-list {
    flex: 1;
    overflow-y: auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
  }

  .map-pin-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 6px 4px;
    border-bottom: 1px solid var(--border);
  }

  .map-pin-item:last-child { border-bottom: none; }

  .map-pin-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-top: 3px;
    flex-shrink: 0;
  }

  .map-pin-meta { flex: 1; min-width: 0; }
  .map-pin-coords { font-family: monospace; color: var(--gold); font-size: 11px; }
  .map-pin-label { color: var(--text-dim); font-size: 11px; word-break: break-word; }

  .map-status {
    font-size: 11px;
    color: var(--text-dim);
    padding: 4px 0;
  }

  .map-notice {
    font-size: 11px;
    color: var(--gold-dim);
    padding: 6px 10px;
    background: rgba(201, 162, 39, 0.08);
    border: 1px solid rgba(201, 162, 39, 0.25);
    border-radius: 6px;
    line-height: 1.45;
  }

  .map-empty {
    text-align: center;
    color: var(--text-dim);
    padding: 40px 20px;
    font-size: 13px;
  }

  .view-settings {
    grid-template-columns: minmax(340px, 0.42fr) minmax(420px, 0.58fr);
    gap: 1px;
    background: var(--border);
  }

  .view-settings.active {
    display: grid;
  }

  .view-play {
    background: var(--border);
    gap: 1px;
  }

  .play-grid {
    display: grid;
    grid-template-columns: minmax(480px, 1.28fr) minmax(380px, 0.72fr);
    flex: 1;
    min-height: 0;
    gap: 1px;
  }

  .settings-config-panel,
  .settings-chronicle-panel {
    background: var(--bg-panel);
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }

  .view-settings .config-scroll {
    flex: 1;
    max-height: none;
    overflow-y: auto;
    padding: 12px 16px 16px;
  }

  .chronicle-full {
    flex: 1;
    overflow-y: auto;
    padding: 8px 16px 16px;
    min-height: 0;
  }

  .panel-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 16px;
    font-family: 'Cinzel', serif;
    font-size: 13px;
    color: var(--gold);
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 1px;
    flex-shrink: 0;
  }

  .header-badges {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-shrink: 0;
  }

  .meta-badge {
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    text-transform: none;
    letter-spacing: 0;
    padding: 3px 8px;
    border-radius: 999px;
    border: 1px solid var(--purple);
    color: var(--purple);
    background: rgba(128, 96, 192, 0.12);
    white-space: nowrap;
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .meta-badge.meta-model {
    border-color: var(--blue);
    color: var(--blue);
    background: rgba(64, 128, 192, 0.12);
    max-width: 200px;
  }

  .chronicle-banner {
    display: flex;
    align-items: stretch;
    height: 40px;
    flex-shrink: 0;
    background: #0d0d14;
    border-top: 1px solid var(--border);
    overflow: hidden;
    cursor: pointer;
  }

  .chronicle-banner:hover .banner-label {
    color: var(--gold);
  }

  .banner-label {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    padding: 0 14px;
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--gold-dim);
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
  }

  .banner-track {
    flex: 1;
    overflow: hidden;
    position: relative;
    mask-image: linear-gradient(90deg, transparent, #000 24px, #000 calc(100% - 24px), transparent);
  }

  .banner-stream {
    display: inline-flex;
    align-items: center;
    gap: 0;
    height: 100%;
    white-space: nowrap;
    animation: banner-scroll 55s linear infinite;
    padding-left: 100%;
  }

  .banner-stream:hover {
    animation-play-state: paused;
  }

  .banner-item {
    font-size: 11px;
    font-family: monospace;
    color: var(--text);
    padding: 0 8px;
  }

  .banner-item.ok { color: var(--green); }
  .banner-item.fail { color: var(--red); }
  .banner-item.chat { color: var(--purple); }
  .banner-item.banner-dim { color: var(--text-dim); font-family: 'Inter', sans-serif; }

  .banner-sep {
    color: var(--border);
    font-size: 8px;
    padding: 0 12px;
    user-select: none;
  }

  @keyframes banner-scroll {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
  }

  header h1 {
    font-family: 'Cinzel', serif;
    font-size: 22px;
    color: var(--gold);
    letter-spacing: 2px;
    text-transform: uppercase;
  }

  header .status {
    display: flex;
    gap: 16px;
    align-items: center;
    font-size: 12px;
  }

  .btn {
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-family: 'Inter', sans-serif;
    transition: all 0.2s;
  }

  .btn:hover {
    background: var(--border);
    border-color: var(--gold-dim);
  }

  .btn-danger {
    border-color: var(--red);
    color: var(--red);
  }

  .btn-danger:hover {
    background: var(--red);
    color: var(--bg-dark);
  }

  .config-grid {
    display: grid;
    gap: 8px;
  }

  .config-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #1a1a2a;
    font-size: 12px;
  }

  .config-label {
    color: var(--text-dim);
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 1px;
  }

  .config-value {
    color: var(--text-bright);
    font-family: monospace;
    text-align: right;
    word-break: break-all;
    max-width: 58%;
  }

  .config-select {
    background: var(--bg-dark);
    border: 1px solid var(--border);
    color: var(--text-bright);
    padding: 6px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-family: monospace;
    width: 100%;
    min-width: 0;
  }

  .config-actions {
    display: flex;
    gap: 8px;
    margin-top: 8px;
    flex-wrap: wrap;
  }

  .config-hint {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 6px;
    line-height: 1.4;
  }

  .provider-tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 8px;
  }

  .provider-tab {
    flex: 1;
    padding: 6px 8px;
    background: var(--bg-dark);
    border: 1px solid var(--border);
    color: var(--text-dim);
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    text-align: center;
  }

  .provider-tab.active {
    border-color: var(--gold);
    color: var(--gold);
    background: var(--bg-card);
  }

  .config-scroll {
    padding: 10px 14px 12px;
    overflow-y: auto;
    flex: 0 0 auto;
  }

  .thoughts-wrap {
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    flex: 1;
  }

  /* .panel sets flex — must override when using grid sub-layouts */
  .panel.left-panel,
  .panel.deliberations-panel {
    display: grid;
  }

  .provider-panel { display: none; }
  .provider-panel.active { display: block; }

  .kingdom-stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
  }

  .kingdom-stats-row .stat-card {
    padding: 6px 8px;
  }

  .kingdom-stats-row .stat-value {
    font-size: 16px;
  }

  .kingdom-resources {
    margin-top: 8px;
    font-size: 11px;
    color: var(--text-dim);
  }

  .kingdom-resources summary {
    cursor: pointer;
    color: var(--gold-dim);
    user-select: none;
  }

  .chat-turn {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
  }

  .apply-ok {
    color: var(--green);
    font-size: 11px;
  }

  .btn-wake {
    border-color: var(--blue);
    color: var(--blue);
  }

  .btn-wake:hover {
    background: var(--blue);
    color: var(--bg-dark);
  }

  .btn-wake:disabled {
    opacity: 0.5;
    cursor: wait;
  }

  .order-box {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 16px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-panel);
  }

  .order-input {
    background: var(--bg-dark);
    border: 1px solid var(--border);
    color: var(--text-bright);
    padding: 8px;
    border-radius: 4px;
    font-size: 12px;
    font-family: 'Inter', sans-serif;
    resize: vertical;
    min-height: 52px;
  }

  .order-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .order-hint {
    font-size: 10px;
    color: var(--text-dim);
    flex: 1;
  }

  .order-queue {
    font-size: 11px;
    color: var(--gold-dim);
    max-height: 40px;
    overflow-y: auto;
    flex-shrink: 0;
    padding: 0 16px;
  }

  .chat-panel {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px 16px 16px;
    font-size: 13px;
    line-height: 1.5;
  }

  /* Left column: compact kingdom stats on top, chat fills the rest */
  .left-panel {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-height: 0;
    overflow: hidden;
  }

  .kingdom-block {
    flex-shrink: 0;
    border-bottom: 1px solid var(--border);
  }

  .kingdom-body {
    padding: 8px 12px 10px;
    overflow: hidden;
    max-height: none;
  }

  .chat-section {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto auto;
    min-height: 0;
    overflow: hidden;
    background: var(--bg-panel);
  }

  .chat-compose {
    padding: 8px 16px 12px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .settings-section {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
  }

  .settings-section:last-child {
    border-bottom: none;
  }

  .settings-section-title {
    font-family: 'Cinzel', serif;
    font-size: 11px;
    color: var(--gold);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 10px;
  }

  .settings-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .settings-bar .provider-tabs {
    margin: 0;
    flex-wrap: wrap;
  }

  .settings-bar .provider-tab {
    padding: 4px 10px;
    font-size: 10px;
  }

  .settings-bar-label {
    font-size: 10px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    min-width: 52px;
  }

  .settings-hint {
    font-size: 10px;
    color: var(--text-dim);
    width: 100%;
    margin-top: 4px;
  }

  .settings-bar .monitor-tab.disconnected {
    opacity: 0.45;
    text-decoration: line-through;
  }

  .settings-bar .mode-tab.active {
    border-color: var(--gold);
    color: var(--gold);
    background: rgba(201, 162, 39, 0.12);
  }

  .screenshot-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .screenshot-preview {
    display: none;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
  }

  .screenshot-preview.visible {
    display: flex;
  }

  .screenshot-preview img {
    max-height: 48px;
    max-width: 80px;
    border-radius: 3px;
    border: 1px solid var(--border);
  }

  .screenshot-preview .screenshot-name {
    font-size: 10px;
    color: var(--text-dim);
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .btn-icon {
    padding: 5px 10px;
    font-size: 11px;
  }

  .chat-compose-inner {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .chat-compose {
    flex-shrink: 0;
    background: var(--bg-dark);
  }

  .chat-section .order-input {
    min-height: 64px;
    max-height: 120px;
    font-size: 13px;
    line-height: 1.45;
  }

  .chat-empty {
    color: var(--text-dim);
    text-align: center;
    margin: auto;
    padding: 24px 16px;
    font-size: 13px;
    line-height: 1.5;
    max-width: 420px;
  }

  .chat-bubble {
    padding: 10px 12px;
    border-radius: 8px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .chat-bubble.user {
    background: #1a2433;
    border-left: 3px solid var(--blue);
    color: var(--text);
  }

  .chat-bubble.overlord {
    background: #221a2e;
    border-left: 3px solid var(--purple);
    color: var(--text-bright);
  }

  .chat-bubble .chat-label {
    font-size: 11px;
    color: var(--gold-dim);
    font-weight: 600;
    display: inline;
    margin-right: 0.35em;
    text-transform: none;
    letter-spacing: 0;
  }

  .chat-bubble .chat-body {
    display: inline;
  }

  .memory-panel {
    font-size: 11px;
    font-family: monospace;
    color: var(--text-dim);
    max-height: 120px;
    overflow-y: auto;
    line-height: 1.45;
    white-space: pre-wrap;
  }

  .memory-entry-failure { color: var(--red); }
  .memory-entry-order { color: var(--gold); }
  .memory-entry-tick { color: var(--text); }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 4px;
  }

  .status-dot.online { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .status-dot.offline { background: var(--red); box-shadow: 0 0 6px var(--red); }

  .panel {
    background: var(--bg-panel);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .panel-header {
    padding: 10px 16px;
    font-family: 'Cinzel', serif;
    font-size: 13px;
    color: var(--gold);
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 1px;
    flex-shrink: 0;
  }

  .panel-body {
    padding: 12px 16px;
    overflow-y: auto;
    flex: 1;
  }

  /* State panel */
  .stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 10px 12px;
  }

  .stat-label {
    font-size: 10px;
    text-transform: uppercase;
    color: var(--text-dim);
    letter-spacing: 1px;
    margin-bottom: 4px;
  }

  .stat-value {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-bright);
  }

  /* LLM Thoughts */
  .thought-bubble {
    background: var(--bg-card);
    border-left: 3px solid var(--purple);
    padding: 12px 16px;
    margin-bottom: 10px;
    border-radius: 0 4px 4px 0;
    animation: fadeIn 0.3s ease;
  }

  .thought-mood {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
  }

  .mood-confident { color: var(--gold); }
  .mood-cautious { color: var(--blue); }
  .mood-aggressive { color: var(--red); }
  .mood-worried { color: #c08040; }
  .mood-pleased { color: var(--green); }
  .mood-frustrated { color: var(--red); }
  .mood-neutral { color: var(--text-dim); }

  .thought-text {
    font-size: 13px;
    line-height: 1.5;
    color: var(--text);
  }

  /* Command history */
  .command-entry {
    display: flex;
    gap: 8px;
    align-items: flex-start;
    padding: 6px 0;
    border-bottom: 1px solid #1a1a2a;
    animation: fadeIn 0.2s ease;
  }

  .command-tick {
    color: var(--text-dim);
    font-size: 11px;
    min-width: 40px;
    font-family: monospace;
  }

  .command-action {
    background: var(--bg-card);
    border: 1px solid var(--border);
    padding: 3px 8px;
    border-radius: 3px;
    font-size: 12px;
    font-family: monospace;
  }

  .command-result {
    font-size: 11px;
  }

  .command-result.ok { color: var(--green); }
  .command-result.fail { color: var(--red); }

  .command-entry-chat .command-tick {
    color: var(--purple);
    min-width: 36px;
  }

  .command-entry-chat .command-action {
    flex: 1;
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    border-color: #2a2040;
  }

  .command-entry-chat .command-result {
    color: var(--text-dim);
    font-size: 11px;
    max-width: 45%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Resources */
  .resource-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }

  .resource-name {
    font-size: 12px;
    min-width: 100px;
    color: var(--text-dim);
  }

  .resource-fill {
    flex: 1;
    height: 6px;
    background: var(--bg-dark);
    border-radius: 3px;
    overflow: hidden;
  }

  .resource-fill-inner {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease;
  }

  .resource-count {
    font-size: 12px;
    font-family: monospace;
    min-width: 50px;
    text-align: right;
  }

  /* Connection overlay */
  .overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(10, 10, 15, 0.95);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }

  .overlay.hidden { display: none; }

  .overlay h2 {
    font-family: 'Cinzel', serif;
    color: var(--gold);
    font-size: 24px;
    margin-bottom: 12px;
  }

  .overlay p {
    color: var(--text-dim);
    font-size: 14px;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .thinking { animation: pulse 1.5s infinite; }

  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg-dark); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>

<header>
  <div class="header-left">
    <h1>Syx LLM Overlord</h1>
    <nav class="main-tabs">
      <button type="button" class="main-tab active" data-view="play" onclick="switchView('play')">Overlord</button>
      <button type="button" class="main-tab" data-view="map" onclick="switchView('map')">Map</button>
      <button type="button" class="main-tab" data-view="settings" onclick="switchView('settings')">Settings &amp; Chronicle</button>
    </nav>
  </div>
  <div class="status">
    <span><span class="status-dot" id="gameStatus"></span> Game</span>
    <span><span class="status-dot" id="llmStatus"></span> LLM</span>
    <span id="tickCounter" style="color: var(--text-dim); font-family: monospace;">Tick: --</span>
    <button class="btn btn-danger" onclick="restartGame()">⟳ Restart Game</button>
  </div>
</header>

<div class="app-shell">
  <!-- Play view: kingdom + chat + deliberations + ticker banner -->
  <div id="viewPlay" class="view view-play active">
    <div class="play-grid">
      <div class="panel left-panel">
        <div class="kingdom-block">
          <div class="panel-header">Kingdom Status</div>
          <div class="kingdom-body" id="statePanel">
            <div class="kingdom-stats-row">
              <div class="stat-card">
                <div class="stat-label">Population</div>
                <div class="stat-value" id="statPop">--</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">Day / Year</div>
                <div class="stat-value" id="statTime">--</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">Happiness</div>
                <div class="stat-value" id="statHappy">--</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">Military</div>
                <div class="stat-value" id="statMilitary">--</div>
              </div>
            </div>
            <details class="kingdom-resources">
              <summary>Resources</summary>
              <div id="resourcesList" style="margin-top:6px;"></div>
            </details>
          </div>
        </div>

        <div class="chat-section">
          <div class="panel-header-row">
            <span>Talk to the Overlord</span>
            <span class="header-badges">
              <span class="meta-badge" id="badgeGameMode" title="Active game mode">—</span>
              <span class="meta-badge" id="badgePersona" title="Active persona">—</span>
              <span class="meta-badge meta-model" id="badgeModel" title="Active model">—</span>
            </span>
          </div>
          <div class="chat-panel" id="chatPanel">
            <div class="chat-empty" id="chatEmpty">No messages yet — ask the Overlord anything, or give a build order.</div>
          </div>
          <div class="order-queue" id="orderQueue"></div>
          <div class="chat-compose">
            <div class="screenshot-preview" id="screenshotPreview">
              <img id="screenshotThumb" src="" alt="Attached screenshot">
              <span class="screenshot-name" id="screenshotName">screenshot.png</span>
              <button class="btn btn-icon" type="button" onclick="clearScreenshot()" title="Remove attachment">✕</button>
            </div>
            <textarea class="order-input" id="orderInput" placeholder="Ask a question or give an order… (Enter to send)"></textarea>
            <div class="order-actions">
              <input type="file" id="screenshotUpload" accept="image/png,image/jpeg,image/webp,image/gif" hidden>
              <button class="btn btn-icon" type="button" onclick="document.getElementById('screenshotUpload').click()">Upload image</button>
              <button class="btn btn-icon" type="button" onclick="captureScreenshot()">Capture game</button>
              <button class="btn" onclick="sendOrder()">Send</button>
              <button class="btn" onclick="clearOrders()">Clear queue</button>
            </div>
          </div>
        </div>
      </div>

      <div class="panel deliberations-panel">
        <div class="thoughts-wrap">
          <div class="panel-header">LLM Deliberations</div>
          <div class="panel-body" id="thoughtsPanel" style="overflow-y: auto; flex: 1;">
            <div style="color: var(--text-dim); text-align: center; margin-top: 20px;">
              Awaiting first decision...
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="chronicle-banner" onclick="switchView('settings')" title="Open full chronicle">
      <div class="banner-label">Chronicle</div>
      <div class="banner-track">
        <div class="banner-stream" id="bannerStream">
          <span class="banner-item banner-dim">Awaiting commands…</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Map view: tile grid + player pins -->
  <div id="viewMap" class="view view-map">
    <div class="map-toolbar">
      <span style="font-family:Cinzel,serif;color:var(--gold);font-size:12px;">Settlement map</span>
      <label>Pin type
        <select id="mapPinType">
          <option value="farm">Farm</option>
          <option value="home">Home</option>
          <option value="well">Well</option>
          <option value="stockpile">Stockpile</option>
          <option value="woodcutter">Woodcutter</option>
          <option value="custom">Custom</option>
        </select>
      </label>
      <label>Zoom
        <input type="range" id="mapCellSize" min="6" max="36" value="14" oninput="onMapZoomInput()">
      </label>
      <button class="btn btn-icon" type="button" onclick="fitMapView()">Fit view</button>
      <button class="btn btn-icon" onclick="refreshMapView()">↻ Refresh</button>
      <button class="btn btn-icon" onclick="queueAllMapPins()">Tell Overlord</button>
      <button class="btn btn-icon" onclick="clearAllMapPins()">Clear pins</button>
      <div class="map-legend" id="mapLegendBar"></div>
    </div>
    <div class="map-notice" id="mapNotice">
      Full settlement map for you to place pins. The Overlord does <strong>not</strong> receive this ASCII grid
      (partial crops confused placement) — use <strong>Tell Overlord</strong> on pins, or chat orders with coordinates.
    </div>
    <div class="map-status" id="mapStatus">Loading map…</div>
    <div class="map-layout">
      <div class="map-scroll-wrap" id="mapScrollWrap">
        <div class="map-empty" id="mapEmpty">No map data — ensure the game is running with the LLM Overlord mod enabled.</div>
        <div class="map-grid" id="mapGrid" hidden></div>
      </div>
      <div class="map-sidebar">
        <div class="panel-header" style="padding:0 4px;">Your pins</div>
        <div class="map-pin-list" id="mapPinList">
          <div style="color:var(--text-dim);font-size:11px;">Click a tile to place a pin. Click again to remove.</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Settings view: config + full chronicle -->
  <div id="viewSettings" class="view view-settings">
    <div class="settings-config-panel">
      <div class="panel-header">Configuration</div>
      <div class="config-scroll">
        <div class="settings-section" id="gameModeSection">
          <div class="settings-section-title">Game mode</div>
          <div class="settings-bar">
            <div class="provider-tabs" id="gameModeTabs">
              <button type="button" class="provider-tab mode-tab" data-mode="teacher" onclick="selectGameMode('teacher')">Teacher</button>
              <button type="button" class="provider-tab mode-tab" data-mode="civil_flow" onclick="selectGameMode('civil_flow')">Civil Flow</button>
            </div>
            <button class="btn btn-icon" onclick="applyGameMode()">Apply</button>
          </div>
          <div class="settings-hint" id="gameModeHint">Civil Flow = win-any-game expert · Teacher = learn while playing</div>
        </div>
        <div class="settings-section" id="monitorSection">
          <div class="settings-section-title">Display monitor</div>
          <div class="settings-bar">
            <div class="provider-tabs" id="monitorTabs">
              <button type="button" class="provider-tab monitor-tab" data-monitor="0" onclick="selectMonitorTab(0)">0</button>
              <button type="button" class="provider-tab monitor-tab" data-monitor="1" onclick="selectMonitorTab(1)">1</button>
              <button type="button" class="provider-tab monitor-tab" data-monitor="2" onclick="selectMonitorTab(2)">2</button>
            </div>
            <button class="btn btn-icon" onclick="applyMonitor(false)">Apply</button>
            <button class="btn btn-icon" onclick="applyMonitor(true)" title="Save monitor + restart game">Apply &amp; restart</button>
          </div>
          <div class="settings-hint" id="monitorHint">Loading monitors…</div>
        </div>
        <div id="configPanel">
          <div style="color: var(--text-dim); text-align: center; padding: 16px;">Loading…</div>
        </div>
      </div>
    </div>
    <div class="settings-chronicle-panel">
      <div class="panel-header">Command Chronicle</div>
      <div class="chronicle-full" id="historyPanel">
        <div style="color: var(--text-dim); text-align: center; padding: 24px;" data-empty="1">
          No commands yet
        </div>
      </div>
    </div>
  </div>
</div>

<div class="overlay hidden" id="overlay">
  <h2 id="overlayTitle">Waiting for Connection</h2>
  <p class="thinking" id="overlayHint">Checking bridge …</p>
  <button type="button" id="overlayDismiss" class="btn" style="margin-top:16px;display:none">Open dashboard anyway</button>
</div>

<script>
const WS_URL = `ws://${location.hostname}:${location.port || (location.protocol === 'https:' ? '443' : '80')}/ws`;
let ws = null;
let reconnectTimer = null;
let tickCount = 0;
let restConnected = false;
let healthPollTimer = null;
let overlayDismissed = false;

async function checkRestHealth() {
  try {
    const resp = await fetch(`${location.origin}/api/health`, { cache: 'no-store' });
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.status === 'ok' ? data : null;
  } catch (e) {
    return null;
  }
}

function setBridgeUi(bridgeUp, gameUp) {
  document.getElementById('llmStatus').className = `status-dot ${bridgeUp ? 'online' : 'offline'}`;
  document.getElementById('gameStatus').className = `status-dot ${gameUp ? 'online' : 'offline'}`;
}

function updateOverlay(health) {
  const overlay = document.getElementById('overlay');
  const hint = document.getElementById('overlayHint');
  const title = document.getElementById('overlayTitle');
  const dismiss = document.getElementById('overlayDismiss');
  if (!overlay) return;

  if (overlayDismissed || health) {
    overlay.classList.add('hidden');
    if (health) {
      setBridgeUi(true, !!health.game_connected);
    }
    return;
  }

  overlay.classList.remove('hidden');
  setBridgeUi(false, false);
  if (title) title.textContent = 'Waiting for Connection';
  if (hint) {
    hint.textContent = `Checking bridge at ${location.origin} … (retrying every 2s)`;
  }
  if (dismiss) dismiss.style.display = 'inline-block';
}

async function pollRestHealth() {
  const health = await checkRestHealth();
  restConnected = !!health;
  if (health) {
    updateOverlay(health);
    try {
      const stateResp = await fetch(`${location.origin}/api/state`);
      if (stateResp.ok) {
        const state = await stateResp.json();
        if (!state.error) updateState(state);
      }
    } catch (e) { /* WS or later poll will refresh */ }
    if (healthPollTimer) {
      clearInterval(healthPollTimer);
      healthPollTimer = null;
    }
  } else {
    updateOverlay(null);
  }
  return health;
}

// REST fallback for the LLM Deliberations panel when the WebSocket is blocked
// (embedded browsers, framed/proxied views, Wave preview pane, etc.). The WS
// drives the panel when connected; this rebuilds it from /api/history otherwise.
let restHistoryTimer = null;
async function pollRestHistory() {
  if (ws && ws.readyState === WebSocket.OPEN) return; // WS drives the panel
  try {
    const resp = await fetch(`${location.origin}/api/history?limit=20`);
    if (!resp.ok) return;
    const data = await resp.json();
    const history = Array.isArray(data) ? data : (data.history || data.entries || []);
    if (!history.length) return;
    const panel = document.getElementById('thoughtsPanel');
    if (!panel) return;
    const bubbles = history.map(h => {
      const d = h.llm_decision || h.decision || {};
      const moodClass = `mood-${d.mood || 'neutral'}`;
      const cmdCount = (d.commands || []).length;
      return `<div class="thought-bubble">
        <div class="thought-mood ${moodClass}">
          #${h.tick_number ?? ''} ${d.mood || 'neutral'} -- ${cmdCount} command${cmdCount !== 1 ? 's' : ''} issued
        </div>
        <div class="thought-text">${d.reasoning || 'No reasoning provided'}</div>
      </div>`;
    }).join('');
    panel.innerHTML = bubbles.substring(0, 8000);
  } catch (e) { /* ignore — WS or next poll will retry */ }
}

async function bootstrapDashboard() {
  document.getElementById('overlayDismiss')?.addEventListener('click', () => {
    overlayDismissed = true;
    updateOverlay({ status: 'ok', game_connected: false });
    setBridgeUi(true, false);
  });

  await pollRestHealth();
  if (!restConnected) {
    healthPollTimer = setInterval(pollRestHealth, 2000);
  }
  connect();
  // REST fallback for deliberations panel when WS is blocked/framed
  restHistoryTimer = setInterval(pollRestHistory, 5000);
  pollRestHistory();
}

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    overlayDismissed = true;
    updateOverlay({ status: 'ok', game_connected: true });
    console.log('Connected to bridge (WebSocket)');
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
  };

  ws.onclose = async () => {
    // Embedded browsers often block WebSocket — stay up if REST works
    const health = await checkRestHealth();
    restConnected = !!health;
    if (health || overlayDismissed) {
      updateOverlay(health || { status: 'ok', game_connected: false });
    } else {
      updateOverlay(null);
    }
    reconnectTimer = setTimeout(connect, 3000);
  };

  ws.onerror = () => ws.close();
}

function handleMessage(data) {
  if (data.type === 'tick') {
    tickCount = data.tick;
    document.getElementById('tickCounter').textContent = `Tick: ${tickCount}`;
    updateState(data.state);
    updateThoughts(data.decision);
    updateHistory(data.tick, data.decision, data.results);
    if (document.getElementById('viewMap')?.classList.contains('active') && data.state?.mapRows?.length) {
      mapCache.rows = data.state.mapRows;
      mapCache.centerX = data.state.mapCenterX;
      mapCache.centerY = data.state.mapCenterY;
      mapCache.radius = data.state.mapRadius;
      mapCache.legend = data.state.mapLegend;
      renderMapGrid();
    }
  } else if (data.type === 'state') {
    updateState(data.state);
  } else if (data.type === 'error') {
    document.getElementById('gameStatus').className = 'status-dot offline';
  } else if (data.type === 'order') {
    renderOrderQueue(data.orders);
  } else if (data.type === 'chat') {
    appendChat(data.user, data.reply, data.id, true, data.screenshot);
    renderOrderQueue(data.orders);
  } else if (data.type === 'persona' || data.type === 'personality') {
    setPersonalityUi(data.persona || data.personality, data.personality_name, data.personality_label);
  } else if (data.type === 'game_mode') {
    cfgCache = {
      ...cfgCache,
      game_mode: data.game_mode,
      game_mode_name: data.game_mode_name,
      game_mode_description: data.game_mode_description,
    };
    renderGameModeTabs(data.game_mode);
    updateMainBadges(cfgCache);
  } else if (data.type === 'monitor') {
    selectedMonitorIndex = data.active_index ?? selectedMonitorIndex;
    renderMonitorTabs(monitorCache, selectedMonitorIndex);
  } else if (data.type === 'map_pins') {
    mapCache.pins = data.pins || [];
    renderMapPinList();
    if (mapCache.rows?.length) renderMapGrid();
  } else if (data.type === 'memory' || data.type === 'memory_cleared') {
    loadMemory();
  }
  if (data.memory_tail) {
    renderMemory(data.memory_tail);
  }
}

function updateState(state) {
  if (!state) return;
  document.getElementById('gameStatus').className = 'status-dot online';

  // Population
  const pop = state.population?.total;
  document.getElementById('statPop').textContent = pop != null ? pop.toLocaleString() : '--';

  // Time
  const day = state.gameTime?.day;
  const year = state.gameTime?.year;
  document.getElementById('statTime').textContent =
    (day != null && year != null) ? `${day} / ${year}` : '--';

  // Happiness
  const happy = state.happiness?.overall;
  document.getElementById('statHappy').textContent =
    happy != null ? `${(happy * 100).toFixed(0)}%` : '--';

  // Military
  const mil = state.military?.divisions;
  document.getElementById('statMilitary').textContent = mil != null ? `${mil} div` : '--';

  // Resources
  const resDiv = document.getElementById('resourcesList');
  if (state.resources && Object.keys(state.resources).length > 0) {
    const entries = Object.entries(state.resources).slice(0, 15);
    const maxVal = Math.max(...entries.map(([_, v]) => Number(v) || 1));
    resDiv.innerHTML = entries.map(([name, val]) => {
      const pct = Math.min(100, (Number(val) / maxVal) * 100);
      const color = pct > 60 ? 'var(--green)' : pct > 30 ? 'var(--gold)' : 'var(--red)';
      return `<div class="resource-bar">
        <span class="resource-name">${name}</span>
        <div class="resource-fill"><div class="resource-fill-inner" style="width:${pct}%;background:${color}"></div></div>
        <span class="resource-count">${Number(val).toLocaleString()}</span>
      </div>`;
    }).join('');
  }
}

function updateThoughts(decision) {
  if (!decision) return;
  const panel = document.getElementById('thoughtsPanel');
  const moodClass = `mood-${decision.mood || 'neutral'}`;
  const cmdCount = (decision.commands || []).length;

  const html = `<div class="thought-bubble">
    <div class="thought-mood ${moodClass}">
      ${decision.mood || 'neutral'} -- ${cmdCount} command${cmdCount !== 1 ? 's' : ''} issued
    </div>
    <div class="thought-text">${decision.reasoning || 'No reasoning provided'}</div>
  </div>` + panel.innerHTML;

  // Keep only last 20 thoughts
  panel.innerHTML = html.substring(0, 8000);
}

function updateHistory(tick, decision, results) {
  const commands = decision?.commands || [];
  if (commands.length === 0) return;

  commands.forEach((cmd, i) => {
    const res = results?.[i];
    const ok = res?.success;
    const msg = res?.message || '';
    const action = `${cmd.action}${cmd.target ? ' ' + cmd.target : ''}`;
    const html = `<div class="command-entry">
      <span class="command-tick">#${tick}</span>
      <span class="command-action">${action}</span>
      <span class="command-result ${ok ? 'ok' : 'fail'}">${ok ? '&#10003;' : '&#10007;'} ${escapeHtml(msg)}</span>
    </div>`;
    const banner = `#${tick} ${action} — ${ok ? 'OK' : 'FAIL'}${msg ? ': ' + msg : ''}`;
    pushChronicle(html, banner, ok ? 'ok' : 'fail');
  });
}

function clearHistoryPlaceholder() {
  const panel = document.getElementById('historyPanel');
  if (!panel) return;
  const empty = panel.querySelector('[data-empty]');
  if (empty) empty.remove();
}

function trimHistoryPanel(panel) {
  if (panel.children.length > 100) {
    panel.innerHTML = Array.from(panel.children).slice(0, 100).map(e => e.outerHTML).join('');
  }
}

const chronicleFeed = [];

function pushChronicle(htmlEntry, bannerText, bannerClass = '') {
  const panel = document.getElementById('historyPanel');
  if (panel) {
    clearHistoryPlaceholder();
    panel.insertAdjacentHTML('afterbegin', htmlEntry);
    trimHistoryPanel(panel);
  }
  chronicleFeed.unshift({ text: bannerText, cls: bannerClass });
  if (chronicleFeed.length > 40) chronicleFeed.pop();
  renderBanner();
}

function renderBanner() {
  const stream = document.getElementById('bannerStream');
  if (!stream) return;
  if (chronicleFeed.length === 0) {
    stream.innerHTML = '<span class="banner-item banner-dim">Awaiting commands…</span>';
    stream.style.animation = 'none';
    return;
  }
  const ordered = [...chronicleFeed].reverse();
  const chunk = ordered.map(item =>
    `<span class="banner-item ${item.cls}">${escapeHtml(item.text)}</span><span class="banner-sep">◆</span>`
  ).join('');
  stream.innerHTML = chunk + chunk;
  stream.style.animation = 'none';
  void stream.offsetWidth;
  const duration = Math.max(28, ordered.length * 6);
  stream.style.animation = `banner-scroll ${duration}s linear infinite`;
}

function updateChatChronicle(user, reply) {
  const shortUser = user.length > 72 ? user.slice(0, 69) + '…' : user;
  const shortReply = reply.length > 96 ? reply.slice(0, 93) + '…' : (reply || '—');
  const html = `<div class="command-entry command-entry-chat">
    <span class="command-tick">chat</span>
    <span class="command-action">You, ${escapeHtml(shortUser)}</span>
    <span class="command-result">→ ${escapeHtml(shortReply)}</span>
  </div>`;
  pushChronicle(html, `chat: ${shortUser} → ${shortReply}`, 'chat');
}

function switchView(view) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.main-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.view === view);
  });
  const targets = { play: 'viewPlay', settings: 'viewSettings', map: 'viewMap' };
  document.getElementById(targets[view] || 'viewPlay')?.classList.add('active');
  if (view === 'map') refreshMapView();
}

function updateMainBadges(cfg) {
  const mode = document.getElementById('badgeGameMode');
  const persona = document.getElementById('badgePersona');
  const model = document.getElementById('badgeModel');
  if (mode) mode.textContent = cfg?.game_mode_name || cfg?.game_mode || '—';
  if (persona) persona.textContent = cfg?.personality_name || cfg?.persona || cfg?.personality || '—';
  if (model) {
    const prov = cfg?.llm_provider || 'ollama';
    model.textContent = formatActiveModel(prov, cfg?.llm_model || '—');
  }
}

const chatSeen = new Set();
let chatSendInFlight = false;
let overlordLabel = 'Overlord,';

// Load config + provider model lists
let currentProvider = 'ollama';
let cfgCache = {};
let selectedMonitorIndex = 0;
let monitorCache = [];
let selectedGameMode = 'civil_flow';

function renderGameModeTabs(activeId) {
  const tabs = document.getElementById('gameModeTabs');
  if (!tabs) return;
  const modes = cfgCache.game_modes || [];
  const active = activeId || cfgCache.game_mode || selectedGameMode;
  if (modes.length) {
    tabs.innerHTML = modes.map(m =>
      `<button type="button" class="provider-tab mode-tab" data-mode="${escapeHtml(m.id)}" onclick="selectGameMode('${escapeHtml(m.id)}')">${escapeHtml(m.name)}</button>`
    ).join('');
  }
  tabs.querySelectorAll('.mode-tab').forEach(btn => {
    const id = btn.dataset.mode;
    btn.classList.toggle('active', id === active);
    const meta = modes.find(m => m.id === id);
    if (meta?.description) btn.title = meta.description;
  });
  selectedGameMode = active;
}

function selectGameMode(modeId) {
  selectedGameMode = modeId;
  renderGameModeTabs(modeId);
}

async function applyGameMode() {
  const hint = document.getElementById('gameModeHint');
  try {
    if (hint) hint.textContent = 'Applying game mode…';
    const resp = await fetch('/api/config/game-mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_mode: selectedGameMode }),
    });
    const result = await resp.json();
    if (result.success) {
      cfgCache = {
        ...cfgCache,
        game_mode: result.game_mode,
        game_mode_name: result.game_mode_name,
        game_mode_description: result.game_mode_description,
      };
      renderGameModeTabs(result.game_mode);
      updateMainBadges(cfgCache);
      const desc = result.game_mode_description || result.game_mode_name;
      if (hint) hint.innerHTML = '<span class="apply-ok">✓ ' + escapeHtml(desc) + '</span>';
    } else {
      if (hint) hint.textContent = 'Failed: ' + (result.message || 'unknown');
    }
  } catch (e) {
    if (hint) hint.textContent = 'Error: ' + e.message;
  }
}

function formatActiveModel(prov, model) {
  if (!model) return '--';
  if (prov === 'openrouter' && model.startsWith('openrouter/')) {
    return model;
  }
  return prov + '/' + model;
}

function formatOpenRouterPrice(raw) {
  const perToken = parseFloat(raw);
  if (Number.isNaN(perToken)) return '';
  if (perToken < 0) return 'varies';
  if (perToken === 0) return 'free';
  const perM = perToken * 1_000_000;
  if (perM >= 1) return `$${perM.toFixed(2)}/M`;
  if (perM >= 0.01) return `$${perM.toFixed(3)}/M`;
  return `$${perM.toFixed(4)}/M`;
}

async function loadConfig() {
  try {
    const resp = await fetch('/api/config');
    const cfg = await resp.json();
    cfgCache = cfg;
    const rawProv = cfg.llm_provider || 'ollama';
    currentProvider = otherProviderIds(cfg).includes(rawProv) ? 'other' : rawProv;
    if (cfg.personality_label) overlordLabel = cfg.personality_label;
    updateMainBadges(cfg);
    renderConfigPanel(cfg);
    selectedGameMode = cfg.game_mode || 'civil_flow';
    renderGameModeTabs(cfg.game_mode);
    if (currentProvider !== 'other') {
      await loadModelsForProvider(currentProvider, cfg.llm_model);
    }
  } catch (e) {
    console.error('Failed to load config:', e);
  }
}

function setPersonalityUi(id, name, label) {
  if (label) overlordLabel = label;
  const sel = document.getElementById('personalitySelect');
  if (sel && id) sel.value = id;
  const active = document.getElementById('activePersonality');
  if (active && name) active.textContent = name;
  updateMainBadges({
    ...cfgCache,
    personality: id || cfgCache.personality,
    personality_name: name || cfgCache.personality_name,
  });
}

function otherProviderIds(cfg) {
  return (cfg.other_providers || []).map(p => p.id);
}

function renderOtherProviderPanel(cfg, selectedId) {
  const others = cfg.other_providers || [];
  if (!others.length) return '<div class="config-hint">No other providers available.</div>';
  const active = others.find(p => p.id === selectedId) || others[0];
  const provOptions = others.map(p =>
    `<option value="${p.id}"${p.id === active.id ? ' selected' : ''}>${escapeHtml(p.label)}</option>`
  ).join('');
  const currentModel = (cfg.llm_provider === active.id && cfg.llm_model) ? cfg.llm_model : (active.model_default || '');
  const currentBaseUrl = (cfg.llm_provider === active.id && cfg.llm_base_url) ? cfg.llm_base_url : (active.base_url_default || '');
  return `
    <select class="config-select" id="otherProviderSelect" onchange="onOtherProviderChange()">${provOptions}</select>
    <div class="config-row" style="border:none;padding:4px 0;">
      <span class="config-label">API Key</span>
      <span class="config-value" id="otherKeyStatus">${active.configured ? 'configured' : `MISSING — set ${escapeHtml(active.env_var)}`}</span>
    </div>
    <input class="config-select" id="otherApiKeyInput" type="password" placeholder="Paste ${escapeHtml(active.env_var)} — saved, never shown again" autocomplete="off">
    <div class="config-actions">
      <button class="btn" onclick="saveOtherApiKey()">Save Key</button>
    </div>
    <input class="config-select" id="otherModelInput" type="text" placeholder="model name" value="${escapeHtml(currentModel)}" style="margin-top:6px;">
    <input class="config-select" id="otherBaseUrlInput" type="text" placeholder="${active.needs_base_url ? 'base_url (required)' : 'base_url (optional override)'}" value="${escapeHtml(currentBaseUrl)}" style="margin-top:6px;">
    <div class="config-actions">
      <button class="btn" onclick="applyOtherProvider()">Apply</button>
    </div>
    <div class="config-hint" id="otherHint">Keys are written to ~/.config/syx-llm-overlord/.env, never to config.yaml.</div>
  `;
}

function renderConfigPanel(cfg) {
  const panel = document.getElementById('configPanel');
  const prov = cfg.llm_provider || 'ollama';
  const isOtherProv = otherProviderIds(cfg).includes(prov);
  const personas = cfg.personalities || [];
  const activePersona = cfg.persona || cfg.personality;
  const opt = (p) => `<option value="${p.id}"${p.id === activePersona ? ' selected' : ''}>${escapeHtml(p.name)}</option>`;
  const persOptions = personas.length
    ? personas.map(opt).join('')
    : '<option value="gregg">Gregg</option>';
  panel.innerHTML = `
    <div class="settings-section" style="padding-top:0;">
      <div class="settings-section-title">LLM model</div>
    <div class="config-row">
      <span class="config-label">Active</span>
      <span class="config-value" id="activeModel">${formatActiveModel(prov, cfg.llm_model)}</span>
    </div>
    <div class="config-row" style="flex-direction: column; align-items: stretch; gap: 6px;">
      <span class="config-label">Persona</span>
      <select class="config-select" id="personalitySelect">${persOptions}</select>
      <div class="config-actions">
        <button class="btn" onclick="applyPersonality()">Apply</button>
      </div>
      <div class="config-hint" id="personalityHint">Voice only — independent of game mode. Active: <span id="activePersonality">${escapeHtml(cfg.personality_name || 'Gregg')}</span></div>
    </div>
    <div class="config-row" style="flex-direction: column; align-items: stretch; gap: 6px;">
      <span class="config-label">Provider</span>
      <div class="provider-tabs">
        <button type="button" class="provider-tab ${prov === 'ollama' ? 'active' : ''}" id="tabOllama" onclick="switchProvider('ollama')">Ollama (local)</button>
        <button type="button" class="provider-tab ${prov === 'openrouter' ? 'active' : ''}" id="tabOpenRouter" onclick="switchProvider('openrouter')">OpenRouter</button>
        <button type="button" class="provider-tab ${isOtherProv ? 'active' : ''}" id="tabOther" onclick="switchProvider('other')">Other</button>
      </div>
      <div class="provider-panel ${prov === 'ollama' ? 'active' : ''}" id="panelOllama">
        <div class="config-row" style="border:none;padding:4px 0;">
          <span class="config-label">Server</span>
          <span class="config-value">${cfg.ollama_url || cfg.ollama_v1_url || '--'}</span>
        </div>
        <select class="config-select" id="ollamaModelSelect"><option>Loading…</option></select>
        <div class="config-actions">
          <button class="btn btn-wake" id="wakeBtn" onclick="wakeOllama()"${prov === 'ollama' ? '' : ' disabled title="Apply Ollama provider first"'}>Wake / Load Model</button>
          <button class="btn" onclick="applyModel()">Apply</button>
          <button class="btn" onclick="refreshModels()">Refresh</button>
        </div>
        <div class="config-hint" id="ollamaHint">${prov === 'ollama' ? 'Cold Ollama? Click Wake first (may take ~2 min).' : 'OpenRouter active — local Ollama is not contacted until you Apply Ollama.'}</div>
      </div>
      <div class="provider-panel ${prov === 'openrouter' ? 'active' : ''}" id="panelOpenRouter">
        <div class="config-row" style="border:none;padding:4px 0;">
          <span class="config-label">API Key</span>
          <span class="config-value">${cfg.openrouter_configured ? 'configured' : 'MISSING — set OPENROUTER_API_KEY'}</span>
        </div>
        <select class="config-select" id="openrouterModelSelect"><option>Loading…</option></select>
        <div class="config-actions">
          <button class="btn" onclick="applyModel()">Apply</button>
          <button class="btn" onclick="refreshModels()">Refresh</button>
        </div>
        <div class="config-hint" id="openrouterHint">OpenRouter free models only (:free tier)</div>
      </div>
      <div class="provider-panel ${isOtherProv ? 'active' : ''}" id="panelOther">
        ${renderOtherProviderPanel(cfg, isOtherProv ? prov : null)}
      </div>
    </div>
    <div class="config-row">
      <span class="config-label">Game API</span>
      <span class="config-value">${cfg.game_url || '--'}</span>
    </div>
    <div class="config-row">
      <span class="config-label">Poll Interval</span>
      <span class="config-value">${cfg.poll_interval || '--'}s</span>
    </div>
    </div>
  `;
}

function switchProvider(prov) {
  currentProvider = prov;
  document.getElementById('tabOllama')?.classList.toggle('active', prov === 'ollama');
  document.getElementById('tabOpenRouter')?.classList.toggle('active', prov === 'openrouter');
  document.getElementById('tabOther')?.classList.toggle('active', prov === 'other');
  document.getElementById('panelOllama')?.classList.toggle('active', prov === 'ollama');
  document.getElementById('panelOpenRouter')?.classList.toggle('active', prov === 'openrouter');
  document.getElementById('panelOther')?.classList.toggle('active', prov === 'other');
  if (prov === 'other') {
    const panel = document.getElementById('panelOther');
    if (panel) panel.innerHTML = renderOtherProviderPanel(cfgCache, otherProviderIds(cfgCache).includes(cfgCache.llm_provider) ? cfgCache.llm_provider : null);
    return;
  }
  const activeModel = cfgCache.llm_provider === prov ? cfgCache.llm_model : null;
  loadModelsForProvider(prov, activeModel);
}

function onOtherProviderChange() {
  const select = document.getElementById('otherProviderSelect');
  const panel = document.getElementById('panelOther');
  if (panel && select) panel.innerHTML = renderOtherProviderPanel(cfgCache, select.value);
}

async function saveOtherApiKey() {
  const providerSelect = document.getElementById('otherProviderSelect');
  const keyInput = document.getElementById('otherApiKeyInput');
  const hint = document.getElementById('otherHint');
  const provider = providerSelect?.value;
  const api_key = keyInput?.value?.trim();
  if (!provider || !api_key) {
    alert('Pick a provider and paste a key first.');
    return;
  }
  try {
    if (hint) hint.textContent = 'Saving key…';
    const resp = await fetch('/api/config/apikey', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key }),
    });
    const result = await resp.json();
    if (result.success) {
      const cfg = await (await fetch('/api/config')).json();
      cfgCache = cfg;
      const panel = document.getElementById('panelOther');
      if (panel) panel.innerHTML = renderOtherProviderPanel(cfgCache, provider);
      const newHint = document.getElementById('otherHint');
      if (newHint) newHint.innerHTML = '<span class="apply-ok">✓ Key saved to ~/.config/syx-llm-overlord/.env</span>';
    } else {
      if (hint) hint.textContent = 'Failed: ' + (result.message || 'unknown');
      alert('Failed: ' + (result.message || 'unknown'));
    }
  } catch (e) {
    if (hint) hint.textContent = 'Error: ' + e.message;
    alert('Save failed: ' + e.message);
  }
}

async function applyOtherProvider() {
  const providerSelect = document.getElementById('otherProviderSelect');
  const modelInput = document.getElementById('otherModelInput');
  const baseUrlInput = document.getElementById('otherBaseUrlInput');
  const hint = document.getElementById('otherHint');
  const provider = providerSelect?.value;
  const model = modelInput?.value?.trim();
  const base_url = baseUrlInput?.value?.trim() || undefined;
  if (!provider || !model) {
    alert('Provider and model are required.');
    return;
  }
  try {
    if (hint) hint.textContent = 'Applying…';
    const resp = await fetch('/api/config/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, model, base_url }),
    });
    const result = await resp.json();
    if (result.success) {
      const cfg = await (await fetch('/api/config')).json();
      cfgCache = cfg;
      currentProvider = 'other';
      const active = document.getElementById('activeModel');
      if (active) active.textContent = formatActiveModel(result.llm_provider, result.llm_model);
      updateMainBadges(cfgCache);
      const panel = document.getElementById('panelOther');
      if (panel) panel.innerHTML = renderOtherProviderPanel(cfgCache, provider);
      const newHint = document.getElementById('otherHint');
      const okMsg = '✓ Applied — ' + result.llm_model;
      if (newHint) newHint.innerHTML = '<span class="apply-ok">' + escapeHtml(okMsg) + '</span>';
    } else {
      if (hint) hint.textContent = 'Apply failed: ' + (result.message || 'unknown');
      alert('Failed: ' + (result.message || 'unknown'));
    }
  } catch (e) {
    if (hint) hint.textContent = 'Apply error: ' + e.message;
    alert('Apply failed: ' + e.message);
  }
}

function setSelectOptions(select, html) {
  if (select) select.innerHTML = html;
}

async function loadModelsForProvider(prov, selectedModel) {
  if (prov === 'openrouter') {
    await loadOpenRouterModels(selectedModel);
  } else {
    await loadOllamaModels(selectedModel);
  }
}

async function loadOllamaModels(selectedModel) {
  const select = document.getElementById('ollamaModelSelect');
  const hint = document.getElementById('ollamaHint');
  const wakeBtn = document.getElementById('wakeBtn');

  if (cfgCache.llm_provider !== 'ollama') {
    const msg = '<option value="">Apply Ollama provider to list models</option>';
    setSelectOptions(select, msg);
    if (hint) hint.textContent = 'OpenRouter is active — local Ollama stays idle until you Apply Ollama.';
    if (wakeBtn) wakeBtn.disabled = true;
    return;
  }
  if (wakeBtn) wakeBtn.disabled = false;

  try {
    const resp = await fetch('/api/ollama/models');
    const data = await resp.json();
    if (data.skipped) {
      const msg = '<option value="">Apply Ollama provider first</option>';
      setSelectOptions(select, msg);
      if (hint) hint.textContent = data.error || 'Ollama not active';
      if (wakeBtn) wakeBtn.disabled = true;
      return;
    }
    if (!data.success) {
      const msg = '<option value="">Ollama unreachable</option>';
      setSelectOptions(select, msg);
      if (hint) hint.textContent = 'Error: ' + (data.error || 'cannot reach Ollama') + ' — try Wake after server is up';
      return;
    }
    const html = data.models.map(m => {
      const label = `${m.name} (${m.params || '?'}, ${m.quant || '?'})`;
      return `<option value="${m.name}"${m.name === selectedModel ? ' selected' : ''}>${label}</option>`;
    }).join('');
    setSelectOptions(select, html);
    const countMsg = `${data.models.length} models — Wake loads selected model into VRAM`;
    if (hint) hint.textContent = countMsg;
  } catch (e) {
    const msg = '<option value="">Failed to load</option>';
    setSelectOptions(select, msg);
    if (hint) hint.textContent = e.message;
  }
}

async function loadOpenRouterModels(selectedModel) {
  const select = document.getElementById('openrouterModelSelect');
  const hint = document.getElementById('openrouterHint');
  const norm = (m) => (m || '').replace(/^openrouter\\/openrouter\\//, 'openrouter/');
  selectedModel = norm(selectedModel);
  try {
    const resp = await fetch('/api/openrouter/models?free_only=true');
    const data = await resp.json();
    if (!data.success) {
      const msg = '<option value="">OpenRouter unavailable</option>';
      setSelectOptions(select, msg);
      if (hint) hint.textContent = data.error || 'cannot list models';
      return;
    }
    const isFreeModel = (m) => {
      const name = (m.name || '').toLowerCase();
      if (name.endsWith(':free') || name === 'openrouter/owl-alpha' || name === 'openrouter/free') return true;
      if (m.prompt_price_label === 'free' && m.completion_price_label === 'free') return true;
      const pin = parseFloat(m.prompt_price);
      const cout = parseFloat(m.completion_price);
      return pin === 0 && cout === 0 && !Number.isNaN(pin) && !Number.isNaN(cout);
    };
    const curated = [
      'nvidia/nemotron-3-super-120b-a12b:free',
      'google/gemma-4-26b-a4b-it:free',
      'openrouter/free',
      'qwen/qwen3-coder:free',
      'meta-llama/llama-3.3-70b-instruct:free',
      'cohere/north-mini-code:free',
      'openai/gpt-oss-120b:free',
      'liquid/lfm-2.5-1.2b-instruct:free',
    ];
    const sorted = [...data.models].filter(isFreeModel).sort((a, b) => {
      const ai = curated.indexOf(a.name);
      const bi = curated.indexOf(b.name);
      if (ai >= 0 && bi >= 0) return ai - bi;
      if (ai >= 0) return -1;
      if (bi >= 0) return 1;
      return a.name.localeCompare(b.name);
    });
    if (!sorted.length) {
      setSelectOptions(select, '<option value="">No free models returned — check OpenRouter key</option>');
      if (hint) hint.textContent = 'No :free models from OpenRouter (rate limits or API issue)';
      return;
    }
    const html = sorted.map(m => {
      const sel = norm(m.name) === selectedModel ? ' selected' : '';
      const pin = m.pinned ? ' [pinned]' : '';
      return `<option value="${m.name}"${sel}>${m.name} (free)${pin}</option>`;
    }).join('');
    setSelectOptions(select, html);
    const countMsg = `${sorted.length} free model${sorted.length === 1 ? '' : 's'} — OpenRouter :free tier only`;
    if (hint) hint.textContent = countMsg;
  } catch (e) {
    const msg = '<option value="">Failed to load</option>';
    setSelectOptions(select, msg);
    if (hint) hint.textContent = e.message;
  }
}

async function refreshModels() {
  const cfg = await (await fetch('/api/config')).json();
  await loadModelsForProvider(currentProvider, cfg.llm_model);
}

async function wakeOllama() {
  if (cfgCache.llm_provider !== 'ollama') {
    alert('Apply Ollama as the active provider first — Wake loads models into local VRAM.');
    return;
  }
  const btn = document.getElementById('wakeBtn');
  const hint = document.getElementById('ollamaHint');
  const select = document.getElementById('ollamaModelSelect');
  const model = select?.value;
  if (btn) { btn.disabled = true; btn.textContent = 'Waking…'; }
  if (hint) hint.textContent = 'Loading model into VRAM — may take 1–3 minutes on a cold Ollama server…';
  try {
    const resp = await fetch('/api/ollama/wake', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: model || undefined }),
    });
    const result = await resp.json();
    if (result.success) {
      if (hint) hint.textContent = result.message + (result.was_loaded ? ' (was already loaded)' : ' (cold load)');
    } else {
      if (hint) hint.textContent = 'Wake failed: ' + (result.error || 'unknown');
      alert('Wake failed: ' + (result.error || 'unknown'));
    }
  } catch (e) {
    if (hint) hint.textContent = 'Wake error: ' + e.message;
    alert('Wake failed: ' + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Wake / Load Model'; }
  }
}

async function applyPersonality() {
  const select = document.getElementById('personalitySelect');
  const hint = document.getElementById('personalityHint');
  const personality = select?.value;
  if (!personality) return;
  try {
    if (hint) hint.textContent = 'Applying persona…';
    const resp = await fetch('/api/config/personality', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ personality }),
    });
    const result = await resp.json();
    if (result.success) {
      cfgCache = { ...cfgCache, persona: result.persona || result.personality, personality: result.personality, personality_name: result.personality_name, personality_label: result.personality_label };
      setPersonalityUi(result.persona || result.personality, result.personality_name, result.personality_label);
      updateMainBadges(cfgCache);
      if (hint) hint.innerHTML = 'Active: <span id="activePersonality">' + escapeHtml(result.personality_name) + '</span> <span class="apply-ok">✓</span>';
    } else {
      if (hint) hint.textContent = 'Failed: ' + (result.message || 'unknown');
      alert('Failed: ' + (result.message || 'unknown'));
    }
  } catch (e) {
    if (hint) hint.textContent = 'Error: ' + e.message;
    alert('Apply failed: ' + e.message);
  }
}

async function applyModel() {
  const hint = currentProvider === 'ollama'
    ? document.getElementById('ollamaHint')
    : document.getElementById('openrouterHint');
  const select = currentProvider === 'ollama'
    ? document.getElementById('ollamaModelSelect')
    : document.getElementById('openrouterModelSelect');
  const model = select?.value;
  if (!model || model.startsWith('Loading') || model.includes('unreachable') || model.includes('Failed') || model.includes('Apply')) {
    alert('Pick a model from the list first (use Refresh if the dropdown is empty).');
    return;
  }

  const cfg = cfgCache.llm_provider ? cfgCache : await (await fetch('/api/config')).json();
  const body = currentProvider === 'ollama'
    ? { provider: 'ollama', model, base_url: cfg.ollama_v1_url }
    : { provider: 'openrouter', model, base_url: cfg.openrouter_url || cfg.llm_base_url };

  const applyBtns = document.querySelectorAll('.config-actions .btn:not(.btn-wake)');
  applyBtns.forEach(b => { b.disabled = true; });

  try {
    if (hint) hint.textContent = 'Applying…';
    const resp = await fetch('/api/config/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const result = await resp.json();
    if (result.success) {
      cfgCache = {
        ...cfg,
        llm_provider: result.llm_provider,
        llm_model: result.llm_model,
        llm_base_url: result.llm_base_url,
      };
      currentProvider = result.llm_provider;
      document.getElementById('tabOllama')?.classList.toggle('active', result.llm_provider === 'ollama');
      document.getElementById('tabOpenRouter')?.classList.toggle('active', result.llm_provider === 'openrouter');
      document.getElementById('panelOllama')?.classList.toggle('active', result.llm_provider === 'ollama');
      document.getElementById('panelOpenRouter')?.classList.toggle('active', result.llm_provider === 'openrouter');
      const active = document.getElementById('activeModel');
      if (active) active.textContent = formatActiveModel(result.llm_provider, result.llm_model);
      updateMainBadges(cfgCache);
      await loadModelsForProvider(result.llm_provider, result.llm_model);
      const okMsg = '✓ Applied — ' + result.llm_model;
      if (hint) hint.innerHTML = '<span class="apply-ok">' + escapeHtml(okMsg) + '</span>';
    } else {
      if (hint) hint.textContent = 'Apply failed: ' + (result.message || 'unknown');
      alert('Failed: ' + (result.message || 'unknown'));
    }
  } catch (e) {
    if (hint) hint.textContent = 'Apply error: ' + e.message;
    alert('Apply failed: ' + e.message);
  } finally {
    applyBtns.forEach(b => { b.disabled = false; });
  }
}

async function loadPendingScreenshot() {
  try {
    const resp = await fetch('/api/screenshot/pending');
    const data = await resp.json();
    const preview = document.getElementById('screenshotPreview');
    const thumb = document.getElementById('screenshotThumb');
    const name = document.getElementById('screenshotName');
    if (data.attached && preview && thumb) {
      preview.classList.add('visible');
      thumb.src = data.preview_url + '?t=' + Date.now();
      if (name) name.textContent = data.filename || 'screenshot';
    } else if (preview) {
      preview.classList.remove('visible');
      if (thumb) thumb.src = '';
    }
  } catch (e) { /* ignore */ }
}

async function clearScreenshot() {
  await fetch('/api/screenshot/pending', { method: 'DELETE' });
  loadPendingScreenshot();
}

async function captureScreenshot() {
  const btn = event?.target;
  if (btn) btn.disabled = true;
  try {
    const resp = await fetch('/api/screenshot', { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      loadPendingScreenshot();
    } else {
      alert('Capture failed: ' + (data.error || 'unknown'));
    }
  } catch (e) {
    alert('Capture failed: ' + e.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function uploadScreenshotFile(file) {
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  try {
    const resp = await fetch('/api/screenshot/upload', { method: 'POST', body: form });
    const data = await resp.json();
    if (data.success) {
      loadPendingScreenshot();
    } else {
      alert('Upload failed: ' + (data.error || 'unknown'));
    }
  } catch (e) {
    alert('Upload failed: ' + e.message);
  }
}

function renderMonitorTabs(monitors, activeIndex) {
  const tabs = document.getElementById('monitorTabs');
  if (!tabs) return;
  monitors.forEach((m) => {
    const btn = tabs.querySelector(`[data-monitor="${m.index}"]`);
    if (!btn) return;
    const status = m.connected ? (m.geometry || m.xrandr) : 'offline';
    btn.textContent = `${m.index} ${m.label}`;
    btn.title = `${m.xrandr} — ${status}`;
    btn.classList.toggle('active', m.index === activeIndex);
    btn.classList.toggle('disconnected', !m.connected);
  });
}

function selectMonitorTab(index) {
  selectedMonitorIndex = index;
  renderMonitorTabs(monitorCache, selectedMonitorIndex);
}

async function loadMonitors() {
  const hint = document.getElementById('monitorHint');
  try {
    const resp = await fetch('/api/monitors');
    const data = await resp.json();
    if (!data.success) {
      if (hint) hint.textContent = data.message || 'Could not load monitors';
      return;
    }
    monitorCache = data.monitors || [];
    selectedMonitorIndex = data.active_index ?? 0;
    renderMonitorTabs(monitorCache, selectedMonitorIndex);
    const active = monitorCache.find(m => m.active);
    const display = data.display || ':0';
    if (hint) {
      hint.textContent = active
        ? `Active: ${active.label} (${active.xrandr}) on ${display}`
        : `DISPLAY=${display}`;
    }
  } catch (e) {
    if (hint) hint.textContent = 'Monitor list unavailable: ' + e.message;
  }
}

async function applyMonitor(restart) {
  const hint = document.getElementById('monitorHint');
  const btns = document.querySelectorAll('#monitorSection .btn');
  btns.forEach(b => { b.disabled = true; });
  try {
    if (hint) hint.textContent = restart ? 'Applying monitor + restarting game…' : 'Applying monitor…';
    const resp = await fetch('/api/monitors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        index: selectedMonitorIndex,
        pin_now: true,
        restart: !!restart,
      }),
    });
    const result = await resp.json();
    if (result.success) {
      await loadMonitors();
      const pinMsg = result.pin?.success
        ? ' Window moved.'
        : result.pin?.message
          ? ' (' + result.pin.message + ')'
          : '';
      const restartMsg = result.restart?.success ? ' Game restarting.' : '';
      if (hint) hint.innerHTML = '<span class="apply-ok">✓ ' + escapeHtml(result.message) + escapeHtml(pinMsg + restartMsg) + '</span>';
    } else {
      if (hint) hint.textContent = 'Failed: ' + (result.message || 'unknown');
      alert('Monitor switch failed: ' + (result.message || 'unknown'));
    }
  } catch (e) {
    if (hint) hint.textContent = 'Error: ' + e.message;
    alert('Monitor switch failed: ' + e.message);
  } finally {
    btns.forEach(b => { b.disabled = false; });
  }
}

async function restartGame() {
  if (!confirm('Restart the game? This will close Songs of Syx and relaunch it with the current settings.')) return;

  try {
    const resp = await fetch('/api/restart', { method: 'POST' });
    const result = await resp.json();
    if (result.success) {
      alert('Game restart initiated — relaunching without stopping the bridge.');
    } else {
      alert('Restart failed: ' + (result.message || 'Unknown error'));
    }
  } catch (e) {
    alert('Restart request failed: ' + e.message);
  }
}

async function sendOrder() {
  const input = document.getElementById('orderInput');
  const msg = input?.value?.trim();
  if (!msg || chatSendInFlight) return;
  chatSendInFlight = true;
  try {
    const resp = await fetch('/api/instruct', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, queue_for_tick: true }),
    });
    const result = await resp.json();
    if (result.success) {
      input.value = '';
      loadPendingScreenshot();
      // WebSocket delivers the chat turn; fallback if disconnected
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        appendChat(msg, result.reply || '(no reply)', result.id, true, result.screenshot);
      }
      renderOrderQueue(result.orders);
      loadMemory();
    } else {
      alert('Failed: ' + (result.message || 'unknown'));
    }
  } catch (e) {
    alert('Send failed: ' + e.message);
  } finally {
    chatSendInFlight = false;
  }
}

function appendChat(user, reply, id, addToChronicle = true, hadScreenshot = false) {
  const key = id || (user + '\0' + (reply || ''));
  if (chatSeen.has(key)) return;
  chatSeen.add(key);

  const el = document.getElementById('chatPanel');
  if (!el) return;
  document.getElementById('chatEmpty')?.remove();
  const wrap = document.createElement('div');
  wrap.className = 'chat-turn';
  wrap.dataset.chatId = id || '';
  const shotTag = hadScreenshot ? ' <span class="chat-shot" title="Screenshot attached">📷</span>' : '';
  wrap.innerHTML =
    (user ? '<div class="chat-bubble user"><span class="chat-label">You,</span> <span class="chat-body">' + escapeHtml(user) + shotTag + '</span></div>' : '') +
    '<div class="chat-bubble overlord"><span class="chat-label">' + escapeHtml(overlordLabel) + '</span> <span class="chat-body">' + escapeHtml(reply || '') + '</span></div>';
  el.appendChild(wrap);
  while (el.querySelectorAll('.chat-turn').length > 24) {
    const removed = el.querySelector('.chat-turn');
    if (removed?.dataset.chatId) chatSeen.delete(removed.dataset.chatId);
    removed?.remove();
  }
  el.scrollTop = el.scrollHeight;
  if (addToChronicle) updateChatChronicle(user, reply || '');
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function loadChat() {
  try {
    const resp = await fetch('/api/chat?limit=20');
    const data = await resp.json();
    const el = document.getElementById('chatPanel');
    if (!el) return;
    el.innerHTML = '';
    chatSeen.clear();
    const msgs = data.messages || [];
    if (msgs.length === 0) {
      el.innerHTML = '<div class="chat-empty" id="chatEmpty">No messages yet — ask the Overlord anything, or give a build order.</div>';
      return;
    }
    for (const m of msgs) {
      appendChat(m.user, m.reply, m.id || m.ts, false, m.screenshot);
    }
  } catch (e) { /* ignore */ }
}

async function clearOrders() {
  await fetch('/api/instruct', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: '', clear: true }),
  });
  renderOrderQueue([]);
}

function renderOrderQueue(orders) {
  const el = document.getElementById('orderQueue');
  if (!el) return;
  if (!orders || orders.length === 0) {
    el.textContent = '';
    return;
  }
  el.textContent = 'Queued: ' + orders.join(' | ');
}

async function loadOrders() {
  try {
    const resp = await fetch('/api/instruct');
    const data = await resp.json();
    renderOrderQueue(data.orders);
  } catch (e) { /* ignore */ }
}

async function loadMemory() {
  try {
    const resp = await fetch('/api/memory?limit=20');
    const data = await resp.json();
    renderMemory(data.entries || []);
  } catch (e) {
    const el = document.getElementById('memoryPanel');
    if (el) el.textContent = 'Memory unavailable';
  }
}

function renderMemory(entries) {
  const el = document.getElementById('memoryPanel');
  if (!el) return;
  if (!el) return;
  if (!entries || entries.length === 0) {
    el.textContent = 'No memory yet — ticks and failures are logged automatically.';
    return;
  }
  el.innerHTML = [...entries].reverse().map(e => {
    const cls = e.kind === 'failure' ? 'memory-entry-failure'
      : e.kind === 'order' ? 'memory-entry-order' : 'memory-entry-tick';
    const prefix = e.tick != null ? `t${e.tick} ` : '';
    return `<div class="${cls}">${prefix}${escapeHtml(e.text || '')}</div>`;
  }).join('');
}

async function clearMemory() {
  if (!confirm('Clear the overlord session memory log?')) return;
  await fetch('/api/memory', { method: 'DELETE' });
  loadMemory();
}

loadConfig();
loadMonitors();
loadOrders();
loadChat();
loadMemory();
loadPendingScreenshot();

document.getElementById('screenshotUpload')?.addEventListener('change', (e) => {
  const file = e.target.files?.[0];
  if (file) uploadScreenshotFile(file);
  e.target.value = '';
});

document.getElementById('orderInput')?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendOrder();
  }
});

// --- Map grid (LLM tile view + player pins) ---
const MAP_TILE_COLORS = {
  'T': '#ffd700',
  '.': '#2d5a27',
  '+': '#8b4513',
  '~': '#1565c0',
  '^': '#1b5e20',
  'M': '#616161',
  'X': '#4a148c',
  '?': '#37474f',
};
const MAP_PIN_TYPE_COLORS = {
  farm: '#4caf50', home: '#ff9800', well: '#29b6f6',
  stockpile: '#8d6e63', woodcutter: '#795548', custom: '#e91e63',
};

let mapCache = { rows: [], centerX: 0, centerY: 0, radius: 0, x1: 0, y1: 0, x2: 0, y2: 0, mapFull: false, legend: '', pins: [], llmMapEnabled: false };
let mapAutoFit = true;

function onMapZoomInput() {
  mapAutoFit = false;
  renderMapGrid();
}

function fitMapView() {
  mapAutoFit = true;
  renderMapGrid();
}

function computeMapCellSize() {
  const slider = document.getElementById('mapCellSize');
  if (!mapAutoFit && slider) {
    return parseInt(slider.value || '14', 10);
  }
  const wrap = document.getElementById('mapScrollWrap');
  const cols = mapCache.rows[0]?.length || 41;
  const rows = mapCache.rows.length || 41;
  if (!wrap || !cols || !rows) return 14;
  const pad = 28;
  const w = Math.max(200, wrap.clientWidth - pad);
  const h = Math.max(200, wrap.clientHeight - pad);
  const byW = Math.floor(w / cols);
  const byH = Math.floor(h / rows);
  const fit = Math.max(6, Math.min(36, Math.min(byW, byH)));
  if (slider) slider.value = String(fit);
  return fit;
}

function initMapLegend() {
  const bar = document.getElementById('mapLegendBar');
  if (!bar) return;
  const items = [
    ['T', 'Throne'], ['.', 'Open'], ['+', 'Room'], ['~', 'Water'],
    ['^', 'Forest'], ['M', 'Mountain'], ['X', 'Blocked'],
  ];
  bar.innerHTML = items.map(([ch, label]) =>
    `<span class="map-legend-item"><span class="map-legend-swatch" style="background:${MAP_TILE_COLORS[ch] || '#333'}"></span>${label}</span>`
  ).join('');
}

function tileColor(ch) {
  if (MAP_TILE_COLORS[ch]) return MAP_TILE_COLORS[ch];
  if (/[A-Za-z0-9]/.test(ch)) return '#6d4c41';
  return '#263238';
}

function pinAt(x, y) {
  return mapCache.pins.find(p => p.x === x && p.y === y);
}

async function refreshMapView() {
  const status = document.getElementById('mapStatus');
  const notice = document.getElementById('mapNotice');
  try {
    const resp = await fetch('/api/map');
    const data = await resp.json();
    if (!data.rows?.length) {
      status.textContent = data.message || 'No map data';
      document.getElementById('mapEmpty').hidden = false;
      document.getElementById('mapGrid').hidden = true;
      mapCache.pins = data.pins || [];
      renderMapPinList();
      return;
    }
    mapCache = {
      rows: data.rows || [],
      centerX: data.centerX ?? 0,
      centerY: data.centerY ?? 0,
      radius: data.radius ?? 0,
      x1: data.x1 ?? 0,
      y1: data.y1 ?? 0,
      x2: data.x2 ?? 0,
      y2: data.y2 ?? 0,
      mapFull: !!data.mapFull,
      legend: data.legend || '',
      pins: data.pins || [],
      llmMapEnabled: !!data.llm_map_enabled,
    };
    const cols = mapCache.rows[0]?.length || 0;
    const rows = mapCache.rows.length;
    if (mapCache.mapFull && mapCache.x2 >= mapCache.x1) {
      status.textContent =
        `Settlement ${cols}×${rows} (x ${mapCache.x1}–${mapCache.x2}, y ${mapCache.y1}–${mapCache.y2}) · throne (${mapCache.centerX}, ${mapCache.centerY})`;
    } else if (mapCache.radius >= 32) {
      status.textContent =
        `Build preview ${cols}×${rows} · ${mapCache.radius} tiles from throne (${mapCache.centerX}, ${mapCache.centerY})`;
    } else {
      status.textContent = `Legacy crop ${rows}×${cols} — restart game for updated mod`;
    }
    if (notice) {
      notice.innerHTML = mapCache.llmMapEnabled
        ? 'Overlord <strong>receives</strong> mapRows (map.llm_enabled: true).'
        : 'For <strong>you</strong> only — Overlord map grid is <strong>OFF</strong>. Pin build sites and click <strong>Tell Overlord</strong>.';
    }
    document.getElementById('mapEmpty').hidden = true;
    document.getElementById('mapGrid').hidden = false;
    mapAutoFit = true;
    renderMapGrid();
    renderMapPinList();
  } catch (e) {
    status.textContent = 'Failed to load map: ' + e.message;
  }
}

function renderMapGrid() {
  const grid = document.getElementById('mapGrid');
  if (!grid || !mapCache.rows?.length) return;
  const cellSize = computeMapCellSize();
  const cols = mapCache.rows[0].length;
  grid.style.gridTemplateColumns = `repeat(${cols}, ${cellSize}px)`;
  grid.innerHTML = '';
  const c0 = mapCache.mapFull && mapCache.x2 >= mapCache.x1
    ? mapCache.x1
    : mapCache.centerX - mapCache.radius;
  const r0 = mapCache.mapFull && mapCache.y2 >= mapCache.y1
    ? mapCache.y1
    : mapCache.centerY - mapCache.radius;

  mapCache.rows.forEach((row, ri) => {
    for (let ci = 0; ci < row.length; ci++) {
      const ch = row[ci];
      const wx = c0 + ci;
      const wy = r0 + ri;
      const pin = pinAt(wx, wy);
      const cell = document.createElement('div');
      cell.className = 'map-cell' + (ch === 'T' ? ' is-throne' : '') + (pin ? ' has-pin' : '');
      cell.style.width = cellSize + 'px';
      cell.style.height = cellSize + 'px';
      cell.style.background = tileColor(ch);
      if (pin) cell.style.setProperty('--pin-color', pin.color || MAP_PIN_TYPE_COLORS[pin.pin_type] || '#e91e63');
      const pinNote = pin ? ` · PIN: ${pin.pin_type} ${pin.label}` : '';
      cell.title = `(${wx}, ${wy}) ${ch}${pinNote}`;
      cell.dataset.x = String(wx);
      cell.dataset.y = String(wy);
      cell.onclick = () => onMapCellClick(wx, wy);
      grid.appendChild(cell);
    }
  });
}

function renderMapPinList() {
  const list = document.getElementById('mapPinList');
  if (!list) return;
  if (!mapCache.pins.length) {
    list.innerHTML = '<div style="color:var(--text-dim);font-size:11px;">Click a tile to place a pin. Click again to remove.</div>';
    return;
  }
  list.innerHTML = mapCache.pins.map(p => `
    <div class="map-pin-item">
      <span class="map-pin-dot" style="background:${escapeHtml(p.color || MAP_PIN_TYPE_COLORS[p.pin_type] || '#e91e63')}"></span>
      <div class="map-pin-meta">
        <div class="map-pin-coords">(${p.x}, ${p.y}) · ${escapeHtml(p.pin_type)}</div>
        <div class="map-pin-label">${escapeHtml(p.label)}</div>
      </div>
      <button class="btn btn-icon" type="button" data-pin-id="${escapeHtml(p.id)}" onclick="removeMapPin(this.dataset.pinId)" title="Remove">✕</button>
    </div>
  `).join('');
}

async function onMapCellClick(x, y) {
  const existing = pinAt(x, y);
  if (existing) {
    await removeMapPin(existing.id);
    return;
  }
  const pinType = document.getElementById('mapPinType')?.value || 'custom';
  let label = pinType === 'custom' ? prompt('Pin label (optional):', 'build here') : pinType;
  if (label === null) return;
  if (!label) label = pinType;
  try {
    const resp = await fetch('/api/map/pins', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x, y, label, pin_type: pinType, queue: false }),
    });
    const data = await resp.json();
    if (data.success) {
      mapCache.pins = data.pins || [];
      renderMapGrid();
      renderMapPinList();
    }
  } catch (e) {
    alert('Failed to place pin: ' + e.message);
  }
}

async function removeMapPin(pinId) {
  try {
    const resp = await fetch('/api/map/pins/' + encodeURIComponent(pinId), { method: 'DELETE' });
    const data = await resp.json();
    mapCache.pins = data.pins || [];
    renderMapGrid();
    renderMapPinList();
  } catch (e) {
    alert('Failed to remove pin: ' + e.message);
  }
}

async function clearAllMapPins() {
  if (!mapCache.pins.length) return;
  if (!confirm('Remove all map pins?')) return;
  try {
    const resp = await fetch('/api/map/pins', { method: 'DELETE' });
    const data = await resp.json();
    mapCache.pins = data.pins || [];
    renderMapGrid();
    renderMapPinList();
  } catch (e) {
    alert('Failed to clear pins: ' + e.message);
  }
}

async function queueAllMapPins() {
  if (!mapCache.pins.length) {
    alert('Place at least one pin first.');
    return;
  }
  try {
    const resp = await fetch('/api/map/pins/queue', { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      renderOrderQueue(data.orders);
      const status = document.getElementById('mapStatus');
      if (status) status.textContent = `Queued ${data.queued?.length || 0} pin(s) for the Overlord.`;
    }
  } catch (e) {
    alert('Failed to queue pins: ' + e.message);
  }
}

initMapLegend();
window.addEventListener('resize', () => {
  if (document.getElementById('viewMap')?.classList.contains('active') && mapCache.rows?.length) {
    renderMapGrid();
  }
});
bootstrapDashboard();
</script>
</body>
</html>
"""
