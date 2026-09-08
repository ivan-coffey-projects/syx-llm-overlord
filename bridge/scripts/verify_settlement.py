#!/usr/bin/env python3
"""Syx settlement vision checkpoint — deterministic anchors + optional vision judge.

Usage:
  python3 verify_settlement.py --health
  python3 verify_settlement.py --json
  python3 verify_settlement.py --image /path/to.png --json

Exit: 0 pass · 1 fail · 2 error
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BRIDGE = os.environ.get("SYX_BRIDGE_URL", "http://127.0.0.1:3847")
MOD = os.environ.get("SYX_MOD_URL", "http://127.0.0.1:47823")
OPENROUTER = os.environ.get("OPENROUTER_API_KEY", "")
VISION_MODEL = os.environ.get("SYX_VISION_MODEL", "google/gemini-2.0-flash-exp:free")

SETTLEMENT_CHECKLIST = (
    "Throne/settlement core visible; last build placement plausible near throne; "
    "terrain fit for room types; no obvious ghost blueprint collisions; "
    "housing/food/water cues; game running not launcher."
)


def _get(url: str, timeout: float = 5.0) -> dict:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def layer1() -> tuple[bool, list[str], dict]:
    issues: list[str] = []
    data: dict = {}
    try:
        data["bridge"] = _get(f"{BRIDGE.rstrip('/')}/api/health")
        data["mod"] = _get(f"{MOD.rstrip('/')}/api/health")
        data["state"] = _get(f"{MOD.rstrip('/')}/api/state")
        data["history"] = _get(f"{BRIDGE.rstrip('/')}/api/history")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return False, [str(e)], data

    if data["bridge"].get("status") != "ok":
        issues.append("bridge not ok")
    if data["mod"].get("status") != "ok":
        issues.append("mod API not ok")

    st = data["state"]
    throne = st.get("throne") or {}
    if throne.get("x") is None or throne.get("y") is None:
        issues.append("throne coordinates missing")
    if not st.get("mapRows"):
        issues.append("mapRows missing — restart game with updated mod")

    hist = data.get("history") or []
    if hist:
        last = hist[-1]
        data["last_tick"] = last.get("tick_number")
        results = last.get("command_results") or []
        data["last_results"] = results
        if results and not any(r.get("success") for r in results):
            if not any(str(r.get("message", "")).startswith("BLOCKED:") for r in results):
                issues.append("last tick: all commands failed")

    ok = not issues
    return ok, issues, data


def _vision_judge(image_path: Path, context: str) -> tuple[dict | None, str | None]:
    if not OPENROUTER:
        return None, "OPENROUTER_API_KEY not set — skipping vision layer"
    b64 = base64.standard_b64encode(image_path.read_bytes()).decode()
    body = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Analyze this Songs of Syx settlement screenshot. {SETTLEMENT_CHECKLIST}\n\n"
                            f"API context:\n{context}\n\n"
                            "End with: VERDICT: {\"pass\": true|false, \"score\": 0-100, "
                            "\"top_issues\": [\"...\"]}"
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 512,
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return None, f"vision HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return None, str(e)

    content = payload["choices"][0]["message"]["content"]
    verdict = None
    for line in content.splitlines():
        if "VERDICT:" in line:
            raw = line.split("VERDICT:", 1)[1].strip()
            try:
                verdict = json.loads(raw)
            except json.JSONDecodeError:
                pass
    return {"critique": content, "verdict": verdict}, None


def main() -> int:
    ap = argparse.ArgumentParser(description="Syx settlement build checkpoint")
    ap.add_argument("--image", help="screenshot PNG (default: latest in logs/screenshots)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--health", action="store_true")
    ap.add_argument("--skip-vision", action="store_true")
    args = ap.parse_args()

    if args.health:
        ok, issues, data = layer1()
        # Health = connectivity + state shape only (not last-tick outcomes)
        health_issues = [i for i in issues if i not in ("last tick: all commands failed",)]
        out = {"layer1_ok": not health_issues, "issues": health_issues, "anchors": {
            "bridge": data.get("bridge"),
            "mod": data.get("mod"),
            "has_map": bool((data.get("state") or {}).get("mapRows")),
        }}
        print(json.dumps(out, indent=2))
        return 0 if not health_issues else 2

    ok1, issues1, data = layer1()
    report: dict = {"layer1_ok": ok1, "layer1_issues": issues1, "anchors": data}

    image_path: Path | None = None
    if args.image:
        image_path = Path(args.image).expanduser()
    else:
        shots = sorted(
            Path(os.environ.get("SYX_SCREENSHOTS_DIR", "")).glob("*.png")
            if os.environ.get("SYX_SCREENSHOTS_DIR")
            else [],
        )
        if not shots:
            default = Path(__file__).resolve().parents[2] / "logs" / "screenshots"
            if default.is_dir():
                shots = sorted(default.glob("*.png"), key=lambda p: p.stat().st_mtime)
        if shots:
            image_path = shots[-1]

    vision_ok = True
    if image_path and image_path.is_file() and not args.skip_vision:
        ctx = json.dumps(
            {
                "throne": (data.get("state") or {}).get("throne"),
                "pop": ((data.get("state") or {}).get("population") or {}).get("total"),
                "last_results": data.get("last_results"),
            },
            indent=2,
        )
        vision, err = _vision_judge(image_path, ctx)
        report["vision_image"] = str(image_path)
        if err:
            report["vision_error"] = err
        elif vision:
            report["vision"] = vision
            v = vision.get("verdict") or {}
            if v.get("pass") is False or (isinstance(v.get("score"), int) and v["score"] < 70):
                vision_ok = False

    passed = ok1 and vision_ok
    report["pass"] = passed

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Layer 1:", "OK" if ok1 else "FAIL", issues1)
        if report.get("vision"):
            print(report["vision"].get("critique", "")[:800])
        elif report.get("vision_error"):
            print("Vision skipped:", report["vision_error"])
        print("PASS" if passed else "FAIL")

    if not ok1:
        return 2
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
