"""Mirror session memory JSONL into an Obsidian-friendly markdown note."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import memory_wiki_path


def render_memory_wiki(entries: list[dict[str, Any]], *, source_path: str) -> str:
    """Build markdown for wiki/memory/live-log.md."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Live session memory",
        "",
        "> Auto-generated from the bridge. Edit `rules/playbook.md` for strategy; "
        "this file is a mirror of runtime learning.",
        "",
        f"- **Source:** `{source_path}`",
        f"- **Updated:** {now}",
        f"- **Entries shown:** {len(entries)} (newest last)",
        "",
        "## Recent events",
        "",
    ]

    if not entries:
        lines.append("_No session memory yet._")
        lines.append("")
        return "\n".join(lines)

    for e in entries:
        kind = e.get("kind", "note")
        tick = e.get("tick")
        day = e.get("day")
        ts = e.get("ts", "")[:19].replace("T", " ")
        text = (e.get("text") or "").replace("\n", " ")

        meta_bits = [f"`{kind}`"]
        if tick is not None:
            meta_bits.append(f"tick {tick}")
        if day is not None:
            meta_bits.append(f"day {day}")
        if ts:
            meta_bits.append(ts)

        prefix = "❌ " if kind == "failure" else "📋 " if kind == "order" else "• "
        lines.append(f"- {prefix}{' · '.join(meta_bits)} — {text}")

    lines.append("")
    lines.append("## Failures only")
    lines.append("")
    failures = [e for e in entries if e.get("kind") == "failure"]
    if failures:
        for e in failures[-20:]:
            lines.append(f"- {e.get('text', '')}")
    else:
        lines.append("_None recorded._")
    lines.append("")
    return "\n".join(lines)


def sync_memory_to_wiki(
    entries: list[dict[str, Any]],
    *,
    source_path: str,
    limit: int = 80,
) -> Path:
    """Write the memory tail to wiki/memory/live-log.md."""
    out = memory_wiki_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    tail = entries[-limit:] if len(entries) > limit else entries
    out.write_text(
        render_memory_wiki(tail, source_path=source_path),
        encoding="utf-8",
    )
    return out
