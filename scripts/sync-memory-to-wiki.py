#!/usr/bin/env python3
"""Standalone memory → wiki sync (for cron, n8n, or manual runs)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))

from bridge.memory import OverlordMemory  # noqa: E402
from bridge.wiki_sync import sync_memory_to_wiki  # noqa: E402


def main() -> int:
    mem = OverlordMemory()
    entries = mem.entries(limit=200)
    out = sync_memory_to_wiki(entries, source_path=str(mem.path))
    print(json.dumps({"ok": True, "entries": len(entries), "wiki": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
