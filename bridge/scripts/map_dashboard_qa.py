#!/usr/bin/env python3
"""Capture dashboard Map tab and verify map API + LLM strip."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output" / "map-qa"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:3847"


def fetch_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=15) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    errors: list[str] = []

    m = fetch_json("/api/map")
    if m.get("llm_map_enabled"):
        errors.append("expected map.llm_map_enabled=false in /api/map")
    rows = m.get("rows") or []
    if not rows:
        errors.append(f"no map rows: {m.get('message', 'empty')}")
    else:
        w, h = len(rows[0]), len(rows)
        print(f"map: {w}x{h} mapFull={m.get('mapFull')} llm_enabled={m.get('llm_map_enabled')}")
        if m.get("mapFull"):
            print(f"bounds x={m.get('x1')}..{m.get('x2')} y={m.get('y1')}..{m.get('y2')}")
        elif w <= 45 and h <= 45:
            errors.append(
                f"map still tiny ({w}x{h}) — restart game after mod install"
            )
        elif w < 64 and not m.get("mapFull"):
            print(f"note: wide preview mode {w}x{h} (expected >=129 when settlement small)")

    # Verify LLM strip via models helper
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from bridge.models import GameState, state_for_llm

    if rows:
        st = GameState(
            mapRows=rows,
            mapRadius=m.get("radius", 0),
            mapFull=bool(m.get("mapFull")),
            mapX1=m.get("x1", 0),
            mapY1=m.get("y1", 0),
            mapX2=m.get("x2", 0),
            mapY2=m.get("y2", 0),
            throne={"x": m.get("centerX", 0), "y": m.get("centerY", 0)},
        )
        stripped = state_for_llm(st, include_map=False)
        if "mapRows" in stripped:
            errors.append("state_for_llm still includes mapRows when disabled")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed — skipping screenshot")
    else:
        shot = OUT / "map-tab.png"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(f"{BASE}/", wait_until="networkidle", timeout=30000)
            page.click('button[data-view="map"]')
            page.wait_for_timeout(1500)
            page.locator("#mapGrid").wait_for(state="visible", timeout=10000)
            page.locator("#mapScrollWrap").screenshot(path=str(shot))
            browser.close()
        print(f"screenshot: {shot}")

    report = {"errors": errors, "map_dims": [len(rows[0]), len(rows)] if rows else None}
    (OUT / "report.json").write_text(json.dumps(report, indent=2))
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
