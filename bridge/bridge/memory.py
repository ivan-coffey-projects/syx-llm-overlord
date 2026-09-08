"""Persistent session memory for the LLM overlord (JSONL log + prompt context)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import memory_path, restart_script_path

DEFAULT_MEMORY_PATH = memory_path()
MAX_ENTRIES = 500
PROMPT_ENTRIES = 30


class OverlordMemory:
    """Append-only memory log read back into LLM prompts."""

    def __init__(self, path: Path | None = None):
        self.path = path or DEFAULT_MEMORY_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(
        self,
        text: str,
        *,
        kind: str = "note",
        tick: int | None = None,
        day: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "text": text.strip(),
        }
        if tick is not None:
            entry["tick"] = tick
        if day is not None:
            entry["day"] = day
        if meta:
            entry["meta"] = meta

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        self._trim()
        return entry

    def log_tick(
        self,
        tick: int,
        day: int | None,
        pop: int | None,
        throne: dict | None,
        reasoning: str,
        commands: list[dict],
        results: list[dict],
        knowledge: Any | None = None,
    ) -> None:
        """Record one decision cycle — failures are highlighted for learning."""
        throne_str = ""
        if throne:
            throne_str = f" throne=({throne.get('x')},{throne.get('y')})"

        summary_parts = []
        for cmd, res in zip(commands, results):
            action = cmd.get("action", "?")
            target = cmd.get("target") or ""
            xy = ""
            if cmd.get("x") is not None and cmd.get("y") is not None:
                xy = f" @({cmd['x']},{cmd['y']})"
            status = "OK" if res.get("success") else "FAIL"
            msg = (res.get("message") or "")[:120]
            summary_parts.append(f"{status} {action} {target}{xy}: {msg}")

        cmd_summary = "; ".join(summary_parts) if summary_parts else "no commands"
        text = (
            f"Tick {tick} day={day} pop={pop}{throne_str}. "
            f"Plan: {reasoning[:200]}. Results: {cmd_summary}"
        )
        self.append(text, kind="tick", tick=tick, day=day)

        for cmd, res in zip(commands, results):
            if res.get("success"):
                continue
            msg = str(res.get("message") or "")
            if msg.startswith("BLOCKED:"):
                continue
            self.append(
                f"FAILED {cmd.get('action')} {cmd.get('target')} "
                f"at ({cmd.get('x')},{cmd.get('y')}): {res.get('message', '')[:150]}",
                kind="failure",
                tick=tick,
                day=day,
            )
            if knowledge is not None:
                knowledge.record_failure(
                    action=str(cmd.get("action") or "build"),
                    target=cmd.get("target"),
                    x=cmd.get("x"),
                    y=cmd.get("y"),
                    message=str(res.get("message") or ""),
                )

    def log_order(self, message: str) -> None:
        self.append(f"Player order: {message}", kind="order")

    def entries(self, limit: int = MAX_ENTRIES) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def for_prompt(self, limit: int = PROMPT_ENTRIES) -> str:
        items = self.entries(limit=limit)
        if not items:
            return "No session memory yet."
        lines = []
        for e in items[-limit:]:
            prefix = f"[{e.get('kind', 'note')}]"
            if e.get("tick") is not None:
                prefix += f" t{e['tick']}"
            if e.get("day") is not None:
                prefix += f" d{e['day']}"
            lines.append(f"{prefix} {e.get('text', '')}")
        return "\n".join(lines)

    def clear(self) -> None:
        self.path.write_text("", encoding="utf-8")

    def _trim(self) -> None:
        items = self.entries(limit=MAX_ENTRIES + 200)
        if len(items) <= MAX_ENTRIES:
            return
        pinned = [e for e in items if e.get("kind") in ("failure", "blocked")]
        rest = [e for e in items if e.get("kind") not in ("failure", "blocked")]
        max_pinned = MAX_ENTRIES // 2
        pinned = pinned[-max_pinned:]
        budget = MAX_ENTRIES - len(pinned)
        trimmed = rest[-budget:] if budget > 0 else []
        combined = sorted(trimmed + pinned, key=lambda e: e.get("ts", ""))
        with open(self.path, "w", encoding="utf-8") as f:
            for e in combined:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
