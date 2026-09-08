"""Songs of Syx starter knowledge injected into the overlord system prompt."""
from __future__ import annotations

from .paths import playbook_path, wiki_dir
from .map_constants import MAX_THRONE_DISTANCE, MIN_THRONE_CLEARANCE

VAULT_PLAYBOOK = playbook_path()

_DEFAULT_PLAYBOOK = f"""
SONGS OF SYX — STARTER PLAYBOOK (follow this until population > 20)

## Core facts
- You control the settlement via JSON commands only. You cannot click the UI.
- Throne coordinates are in game state — ALWAYS anchor builds within ~{MAX_THRONE_DISTANCE} tiles of throne (x,y).
- NEVER build at (0,0) unless throne is at (0,0). Wrong coords cause repeated failures.
- Only `build`, `clear_placement`, and `set_speed` work. set_policy, recruit, set_tax, set_ration, demolish are NOT implemented.
- After placing buildings, always set_speed to 2 (normal) so construction proceeds.
- **Wait for construction to finish.** If `construction.instances` / `area` > 0: **set_speed 2 only** — no new blueprints. The bridge keeps speed at 5x while sites are open. A tiny stuck ghost may be cleared; a large backlog is NOT an excuse to place more.
- Hard limit: builds within {MAX_THRONE_DISTANCE} tiles of throne (bridge guard enforces this).
- **NEVER box in the throne.** Keep every build's footprint at least {MIN_THRONE_CLEARANCE} tiles away from T — building on or ringing the throne traps settlers (they can't path to food/water) and the colony dies even while healthy. The bridge REJECTS builds inside this ring. Valid zone is the ring {MIN_THRONE_CLEARANCE}–{MAX_THRONE_DISTANCE} tiles from throne.
- mapRows shows a {MAX_THRONE_DISTANCE}-tile radius around throne — spread builds across open `.` tiles, not clustered on the throne, and leave open corridors between buildings so settlers can move.

## TmpArea recovery
- TmpArea/_HOME error: clear_placement once, then farm only (farms relocate to open tiles).
- After 8 TmpArea failures bridge enters farms-only mode until recovery.
- Never retry same coordinates. Use mapRows: . = open, + = room, T = throne.
- New game clears session memory and coord blacklist automatically.

## Day 0 priorities (population = 0) — FOOD IS KING
1. Read throne position from state. All x/y in build commands must be near throne.
2. Build **farm_grain** (food) — outdoor area on `.` tiles. Never cotton/industry farms early.
3. Build **canteen** — settlers eat here (ovens placed inside). Homes are blocked until this exists.
4. Build **home** — indoor room, attracts settlers.
5. Build **well** — outdoor single tile; mod spirals outward if TmpArea blocks.
6. Stockpile and woodcutter are blocked by the bridge until pop ≥ 15.
7. After 3 well TmpArea failures, bridge pauses wells — build farm_grain instead.

## Pop 1–14 (growth phase)
- If `resources` is empty / only credits → **another farm**, not another home.
- Focus: farm + canteen secure, then home/well as needed. **Max 1 build per tick.**
- Stockpile after canteen exists (so harvest is stored). Woodcutter blocked until pop ≥ 15.
- If homes fail with TmpArea, clear_placement then farm at a new `.` tile.

## Pop 15+ (industry phase)
- Stockpile on indoor `.` when no overlapping rooms.
- Woodcutter only on ^ tiles visible in mapRows (not on + room tiles).

## Learning (not static rules)
- SESSION MEMORY = failures and orders from THIS game.
- PERSISTENT KNOWLEDGE = blacklisted coords and patterns learned across ALL games (auto-updated). Read both before every build.
- Never retry a blacklisted coordinate. If unsure, pick a new spot 15+ tiles from throne.

## Room types (target names)
- Indoor area: stockpile, home
- Outdoor area: farm, pasture, orchard, woodcutter
- Outdoor single: well, fishery, hunter

## Build command format
{{"action":"build","target":"home","x":386,"y":128,"params":{{"width":4,"height":4}}}}

## Strategy
- One focused goal per tick. Max 1 build + set_speed.
- If last 3 ticks failed, switch to farm or clear_placement.
- Prefer mapRows open `.` tiles spread across the visible map — avoid stacking everything adjacent to T.
"""


def load_playbook() -> str:
    """Load playbook from Obsidian wiki; fall back to embedded default."""
    if VAULT_PLAYBOOK.is_file():
        raw = VAULT_PLAYBOOK.read_text(encoding="utf-8")
        # Strip YAML frontmatter if present
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                raw = parts[2].lstrip("\n")
        return raw.strip()
    return _DEFAULT_PLAYBOOK.strip()


def _strip_frontmatter(raw: str) -> str:
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n").strip()
    return raw.strip()


def _read_wiki(relative: str) -> str:
    path = wiki_dir() / relative
    if path.is_file():
        return _strip_frontmatter(path.read_text(encoding="utf-8"))
    return ""


def load_mode_context(game_mode_id: str) -> str:
    """Extra wiki-backed prompt block for game modes (not personas)."""
    pid = (game_mode_id or "").strip().lower()
    if pid == "teacher":
        body = _read_wiki("modes/teacher.md")
        return f"\n\n--- TEACHER MODE GUIDE ---\n{body}\n" if body else ""
    if pid == "civil_flow":
        chunks = [
            ("CIVIL FLOW STATE — expert doctrine", _read_wiki("modes/civil-flow.md")),
            ("ROOM TYPES (wiki)", _read_wiki("rules/rooms.md")),
            ("FAILURES (wiki)", _read_wiki("rules/failures.md")),
            ("COMMANDS (wiki)", _read_wiki("rules/commands.md")),
        ]
        parts = []
        for title, text in chunks:
            if text:
                parts.append(f"--- {title} ---\n{text}")
        return ("\n\n" + "\n\n".join(parts) + "\n") if parts else ""
    return ""


# Loaded once at import; reload via load_playbook() each tick in llm_brain
SOS_PLAYBOOK = load_playbook()
