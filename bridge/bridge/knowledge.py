"""Persistent knowledge learned across game sessions (auto + optional notes)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import knowledge_path, knowledge_wiki_path

MAX_BLACKLIST = 80
MAX_FACTS = 40
BLACKLIST_AFTER = 2  # failures at same spot before hard blacklist


class OverlordKnowledge:
    """Compact long-term memory — blacklists and facts survive new games."""

    def __init__(self, path: Path | None = None):
        self.path = path or knowledge_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"version": 1, "blacklist": [], "facts": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            data.setdefault("blacklist", [])
            data.setdefault("facts", [])
            return data
        except (json.JSONDecodeError, OSError):
            return {"version": 1, "blacklist": [], "facts": []}

    def _save(self) -> None:
        self._data["updated"] = datetime.now(timezone.utc).isoformat()
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _bl_key(self, action: str, target: str, x: int | None, y: int | None) -> str:
        return f"{action}|{target or ''}|{x}|{y}"

    def record_failure(
        self,
        *,
        action: str,
        target: str | None,
        x: int | None,
        y: int | None,
        message: str,
        persist: bool = True,
    ) -> None:
        """Learn from a failed command — blacklist coords after repeat failures."""
        if action != "build" or x is None or y is None:
            self._maybe_add_pattern_fact(action, target, message)
            if persist:
                self._save()
            return

        key = self._bl_key(action, target or "", x, y)
        reason = self._short_reason(message)
        bl: list[dict] = self._data["blacklist"]
        for entry in bl:
            if entry.get("key") == key:
                entry["count"] = int(entry.get("count", 0)) + 1
                entry["reason"] = reason
                entry["last_ts"] = datetime.now(timezone.utc).isoformat()
                break
        else:
            bl.append({
                "key": key,
                "action": action,
                "target": target or "",
                "x": x,
                "y": y,
                "count": 1,
                "reason": reason,
                "last_ts": datetime.now(timezone.utc).isoformat(),
            })

        bl.sort(key=lambda e: (-int(e.get("count", 0)), e.get("key", "")))
        self._data["blacklist"] = bl[:MAX_BLACKLIST]
        self._maybe_add_pattern_fact(action, target, message)
        if persist:
            self._save()

    def reset_for_new_game(self, throne: dict | None = None, day: int | None = None) -> None:
        """Drop coord blacklist for a fresh settlement; keep learned pattern facts."""
        self._data["blacklist"] = []
        self._data["session"] = {
            "throne": throne,
            "day": day,
            "started": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def clear_all(self) -> None:
        """Full reset including facts."""
        self._data = {"version": 1, "blacklist": [], "facts": []}
        self._save()

    def record_fact(self, text: str) -> None:
        """Manual or LLM-suggested durable fact (deduped)."""
        text = text.strip()
        if not text or len(text) < 8:
            return
        facts: list[dict] = self._data["facts"]
        norm = text.lower()
        for f in facts:
            if f.get("text", "").lower() == norm:
                f["count"] = int(f.get("count", 0)) + 1
                f["last_ts"] = datetime.now(timezone.utc).isoformat()
                break
        else:
            facts.append({
                "text": text,
                "count": 1,
                "last_ts": datetime.now(timezone.utc).isoformat(),
            })
        self._data["facts"] = facts[-MAX_FACTS:]
        self._save()

    def _maybe_add_pattern_fact(self, action: str, target: str | None, message: str) -> None:
        msg = (message or "").lower()
        target = (target or "").lower()

        if "woodcutter" in target or "_woodcutter" in msg:
            if "tree" in msg:
                self._bump_fact("Woodcutter needs trees on the placement tiles — skip if none nearby.", "woodcutter_trees")
            if "storage" in msg or "crates" in msg:
                self._bump_fact("Woodcutter needs storage/crates inside plan — often deadlocks with stockpile early.", "woodcutter_storage")

        if "stockpile" in target or "_stockpile" in msg:
            if "crates" in msg:
                self._bump_fact("Stockpile needs crates placed inside — cannot bootstrap via build alone early.", "stockpile_crates")

        if "tmparea" in msg.replace(" ", "") or "_home error" in msg:
            self._bump_fact("TmpArea/collision = tile saturated — move 10+ tiles away, never retry same coords.", "tmparea")

        if action == "build" and "timed out" in msg:
            self._bump_fact("Build timed out — game thread busy; retry only one command next tick.", "timeout")

    def _bump_fact(self, text: str, fact_id: str) -> None:
        facts: list[dict] = self._data["facts"]
        for f in facts:
            if f.get("id") == fact_id:
                f["count"] = int(f.get("count", 0)) + 1
                f["last_ts"] = datetime.now(timezone.utc).isoformat()
                if int(f["count"]) >= 3 and int(f["count"]) == 3:
                    pass  # already promoted at 3
                return
        facts.append({
            "id": fact_id,
            "text": text,
            "count": 1,
            "last_ts": datetime.now(timezone.utc).isoformat(),
        })
        self._data["facts"] = facts[-MAX_FACTS:]

    @staticmethod
    def _short_reason(message: str) -> str:
        msg = (message or "")[:120]
        if "TmpArea" in msg or "_HOME error" in msg:
            return "collision/TmpArea"
        if "Must not be placed on room" in msg:
            return "blocked by room"
        if "Crates" in msg:
            return "needs crates"
        if "tree" in msg.lower():
            return "needs trees"
        if "timed out" in msg.lower():
            return "timeout"
        return msg.split("(")[0].strip()[:60] or "failed"

    def import_failures_from_memory(self, entries: list[dict[str, Any]]) -> int:
        """Backfill knowledge from JSONL failure entries (e.g. on startup)."""
        n = 0
        for e in entries:
            if e.get("kind") != "failure":
                continue
            parsed = self._parse_failure_text(e.get("text", ""))
            if parsed:
                self.record_failure(**parsed, persist=False)
                n += 1
        self._save()
        return n

    @staticmethod
    def _parse_failure_text(text: str) -> dict[str, Any] | None:
        # FAILED build stockpile at (468,165): message...
        m = re.match(
            r"FAILED\s+(\w+)\s+(\S+)\s+at\s+\((-?\d+),\s*(-?\d+)\):\s*(.*)",
            text.strip(),
            re.I,
        )
        if not m:
            return None
        return {
            "action": m.group(1).lower(),
            "target": m.group(2),
            "x": int(m.group(3)),
            "y": int(m.group(4)),
            "message": m.group(5),
        }

    def is_blocked(
        self,
        action: str,
        target: str | None,
        x: int | None,
        y: int | None,
    ) -> tuple[bool, str | None]:
        """True if command should be rejected pre-flight."""
        if action != "build" or x is None or y is None:
            return False, None

        # Any build blacklisted at this coordinate
        for entry in self._data.get("blacklist", []):
            if int(entry.get("count", 0)) < BLACKLIST_AFTER:
                continue
            if entry.get("x") == x and entry.get("y") == y:
                return True, (
                    f"blacklisted coordinate ({x},{y}) — "
                    f"{entry.get('count')}x {entry.get('reason', 'failed')}"
                )

        # Exact action+target+coord match
        key = self._bl_key(action, target or "", x, y)
        for entry in self._data.get("blacklist", []):
            if entry.get("key") == key and int(entry.get("count", 0)) >= BLACKLIST_AFTER:
                return True, (
                    f"blacklisted {target} @ ({x},{y}) — "
                    f"{entry.get('count')}x {entry.get('reason', 'failed')}"
                )
        return False, None

    def for_prompt(self, limit_blacklist: int = 25, limit_facts: int = 12) -> str:
        bl = [
            e for e in self._data.get("blacklist", [])
            if int(e.get("count", 0)) >= BLACKLIST_AFTER
        ][:limit_blacklist]
        facts = sorted(
            self._data.get("facts", []),
            key=lambda f: -int(f.get("count", 0)),
        )[:limit_facts]

        if not bl and not facts:
            return "No persistent knowledge yet — failures will be learned automatically."

        lines = ["Learned across prior sessions (do not repeat blacklisted builds):"]
        for e in bl:
            lines.append(
                f"- NEVER {e.get('action')} {e.get('target')} @ ({e['x']},{e['y']}) "
                f"— {e.get('count')}x ({e.get('reason', 'failed')})"
            )
        promoted = [f for f in facts if int(f.get("count", 0)) >= 3]
        if promoted:
            lines.append("Patterns:")
            for f in promoted:
                lines.append(f"- {f.get('text')}")
        return "\n".join(lines)

    def snapshot(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "blacklist_count": len(self._data.get("blacklist", [])),
            "facts_count": len(self._data.get("facts", [])),
            "blacklist": self._data.get("blacklist", [])[:30],
            "facts": self._data.get("facts", []),
            "prompt_preview": self.for_prompt(),
        }

    def sync_wiki(self) -> Path | None:
        """Mirror knowledge to wiki/memory/knowledge.md for Obsidian."""
        try:
            out = knowledge_wiki_path()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(self._render_wiki(), encoding="utf-8")
            return out
        except OSError:
            return None

    def _render_wiki(self) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            "# Persistent knowledge",
            "",
            "> Auto-learned from failures across all game sessions. "
            "Playbook stays short; this file grows from experience.",
            "",
            f"- **Source:** `{self.path}`",
            f"- **Updated:** {now}",
            "",
            "## Blacklisted coordinates",
            "",
        ]
        bl = [
            e for e in self._data.get("blacklist", [])
            if int(e.get("count", 0)) >= BLACKLIST_AFTER
        ]
        if bl:
            for e in bl[:40]:
                lines.append(
                    f"- `{e.get('action')} {e.get('target')} @ ({e['x']},{e['y']})` "
                    f"— {e.get('count')}× {e.get('reason', '')}"
                )
        else:
            lines.append("_None yet (need 2+ failures at same spot)._")
        lines.extend(["", "## Patterns", ""])
        facts = sorted(self._data.get("facts", []), key=lambda f: -int(f.get("count", 0)))
        if facts:
            for f in facts:
                lines.append(f"- ({f.get('count', 1)}×) {f.get('text')}")
        else:
            lines.append("_None yet._")
        lines.append("")
        return "\n".join(lines)
