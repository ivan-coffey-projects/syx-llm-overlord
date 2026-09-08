"""Pre-flight command validation before hitting the game mod API."""
from __future__ import annotations

import math
import os
import re
from typing import TYPE_CHECKING

from .map_constants import MAX_THRONE_DISTANCE, MIN_THRONE_CLEARANCE
from .models import Command, GameState

if TYPE_CHECKING:
    from .knowledge import OverlordKnowledge

# Speed the bridge injects when it forces set_speed (paused/slow/construction).
# Levels: 0=pause, 1=1x, 2=5x, 3≈25x, 4=250x.
# Default 1x — 250x (old default) locked the placer and starved colonies before
# a canteen could finish. Overnight mode exports SYX_INJECT_SPEED=4 explicitly.
INJECTED_SPEED = max(0, min(4, int(os.environ.get("SYX_INJECT_SPEED", "1"))))
# Hard cap until food chain is live (canteen exists or pop >= FOOD_READY_POP).
# Level 2 = 5x — enough for construction to finish; level 4 (250x) is overnight-only.
EARLY_SPEED_MAX = 2
FOOD_READY_POP = 20

EARLY_GAME_POP_THRESHOLD = 10
INDUSTRY_POP_THRESHOLD = 15
HEARTH_TARGETS = frozenset({"hearth", "_hearth"})
CANTEEN_TARGETS = frozenset({"canteen", "_canteen", "eatery", "diner", "mess", "dining"})
TMPAREA_FARMS_ONLY_AFTER = 8
TMPAREA_CLEAR_EVERY = 1
FOREST_TILE_CHARS = frozenset({"^"})

# Normalized room tokens blocked until population grows (wood/stockpile handled separately)
EARLY_GAME_BLOCKED = frozenset({
    "hunter", "hunter_normal",
    "pasture", "pasture_aur",
    "fishery", "fishery_normal", "orchard", "orchard_fruit",
    "mine", "mine_clay", "mine_stone", "mine_ore",
    "graveyard", "graveyard_normal", "hauler", "_hauler",
    "import", "export", "transport",
})

WOODCUTTER_TARGETS = frozenset({"woodcutter", "_woodcutter"})
STOCKPILE_TARGETS = frozenset({"stockpile", "_stockpile"})
WELL_TARGETS = frozenset({"well", "wellnormal", "well_normal"})
COTTON_FARM_MARKERS = frozenset({"cotton", "farmcotton"})

WELL_FAIL_BACKOFF_AFTER = 3
WELL_FAIL_BACKOFF_TICKS = 10

# When TmpArea saturation detected — only outdoor area farms relocate successfully
FARMS_ONLY_ALLOWED = frozenset({
    "farm", "pasture", "orchard", "cotton", "farm_cotton",
    "farm_grain", "farm_veg", "farm_herb", "farm_mushroom",
})

# Obvious bad coordinates the LLM hallucinates
BAD_COORDS = frozenset({(0, 0), (100, 100), (300, 300)})

TIMEOUT_BACKOFF_THRESHOLD = 3

HOME_TARGETS = frozenset({"home", "_home", "house", "housing"})
HOME_HEADROOM = 2
BUILD_WAIT_BRIDGE_TICKS = 6
# A site whose (instances, area) hasn't moved for this many bridge ticks is
# treated as stuck (unreachable tiles / dead builders). Auto-clear_placement
# still runs, but we only *unblock new builds* for a small stalled footprint —
# a large backlog that looks "stuck" at 1x is usually just slow builders, and
# unblocking piles more blueprints on top (playtest death spiral).
CONSTRUCTION_STALL_TICKS = 6
CONSTRUCTION_STALL_ESCAPE_MAX_INSTANCES = 2
CONSTRUCTION_STALL_ESCAPE_MAX_AREA = 48

_tmparea_streak = 0
_farms_only = False
_well_fail_streak = 0
_well_blocked_ticks = 0
_build_wait_ticks = 0
_construction_sig: tuple[int, int] | None = None
_construction_stall_ticks = 0
_session_build_counts: dict[str, int] = {
    "home": 0, "farm": 0, "well": 0, "hearth": 0, "canteen": 0,
}


def reset_session_guard() -> None:
    """Clear TmpArea / farms-only state for a new game."""
    global _tmparea_streak, _farms_only, _well_fail_streak, _well_blocked_ticks, _session_build_counts, _build_wait_ticks
    global _construction_sig, _construction_stall_ticks
    _tmparea_streak = 0
    _farms_only = False
    _well_fail_streak = 0
    _well_blocked_ticks = 0
    _build_wait_ticks = 0
    _construction_sig = None
    _construction_stall_ticks = 0
    _session_build_counts = {
        "home": 0, "farm": 0, "well": 0, "hearth": 0, "canteen": 0,
    }


def tick_guard_cooldowns(state: GameState | None = None) -> None:
    """Call once per bridge decision tick."""
    global _well_blocked_ticks, _build_wait_ticks, _construction_sig, _construction_stall_ticks
    if _well_blocked_ticks > 0:
        _well_blocked_ticks -= 1
    if state is not None:
        sig = _construction_signature(state)
        if sig is None:
            _construction_sig = None
            _construction_stall_ticks = 0
        elif sig == _construction_sig:
            _construction_stall_ticks += 1
        else:
            _construction_sig = sig
            _construction_stall_ticks = 0
    if state is not None and not _construction_pending(state):
        _build_wait_ticks = 0
    elif _build_wait_ticks > 0:
        _build_wait_ticks -= 1


def farms_only_active() -> bool:
    return _farms_only


def should_clear_placement() -> bool:
    """Auto-send clear_placement every N TmpArea failures."""
    return _tmparea_streak > 0 and _tmparea_streak % TMPAREA_CLEAR_EVERY == 0


def should_clear_stuck_construction() -> bool:
    """True when construction signature hasn't moved for CONSTRUCTION_STALL_TICKS.
    Caller should inject builder speed + clear_placement; builds stay blocked for
    large backlogs (see _construction_pending escape hatch)."""
    return _construction_sig is not None and _construction_stall_ticks >= CONSTRUCTION_STALL_TICKS


def record_clear_placement_outcome(success: bool) -> None:
    """Exit farms-only mode once TmpArea ghosts are cleared in-game."""
    global _tmparea_streak, _farms_only
    if success:
        _tmparea_streak = 0
        _farms_only = False


def record_build_outcome(success: bool, message: str, target: str | None) -> None:
    """Track TmpArea streak and enable farms-only mode."""
    global _tmparea_streak, _farms_only, _well_fail_streak, _well_blocked_ticks, _session_build_counts, _build_wait_ticks
    msg = (message or "").lower()
    norm = _normalize_target(target)
    if success:
        _tmparea_streak = max(0, _tmparea_streak - 2)
        if _is_well_target(norm):
            _well_fail_streak = 0
        _count_successful_build(message or "")
        _build_wait_ticks = BUILD_WAIT_BRIDGE_TICKS
        return
    if _is_well_target(norm) and (
        "tmparea" in msg.replace(" ", "") or "well" in msg and "error" in msg
    ):
        _well_fail_streak += 1
        if _well_fail_streak >= WELL_FAIL_BACKOFF_AFTER:
            _well_blocked_ticks = WELL_FAIL_BACKOFF_TICKS
    if "tmparea" in msg.replace(" ", "") or "_home error" in msg or "collision" in msg:
        _tmparea_streak += 1
        if _tmparea_streak >= TMPAREA_FARMS_ONLY_AFTER:
            _farms_only = True


def guard_status() -> dict:
    return {
        "tmparea_streak": _tmparea_streak,
        "farms_only": _farms_only,
        "max_throne_distance": MAX_THRONE_DISTANCE,
        "min_throne_clearance": MIN_THRONE_CLEARANCE,
        "industry_pop_threshold": INDUSTRY_POP_THRESHOLD,
        "well_blocked_ticks": _well_blocked_ticks,
        "well_fail_streak": _well_fail_streak,
        "build_wait_ticks": _build_wait_ticks,
        "construction_stall_ticks": _construction_stall_ticks,
        "session_builds": dict(_session_build_counts),
        "injected_speed": INJECTED_SPEED,
        "early_speed_max": EARLY_SPEED_MAX,
        "food_ready_pop": FOOD_READY_POP,
    }


def _construction_signature(state: GameState) -> tuple[int, int] | None:
    con = state.construction or {}
    try:
        instances = int(con.get("instances") or 0)
        area = int(con.get("area") or 0)
    except (TypeError, ValueError):
        return None
    if instances <= 0 and area <= 0:
        return None
    return instances, area


def _construction_pending(state: GameState) -> bool:
    sig = _construction_signature(state)
    if sig is None:
        return False
    instances, area = sig
    # Escape hatch: tiny stalled ghost — let the LLM place elsewhere.
    if (
        _construction_stall_ticks >= CONSTRUCTION_STALL_TICKS
        and instances <= CONSTRUCTION_STALL_ESCAPE_MAX_INSTANCES
        and area <= CONSTRUCTION_STALL_ESCAPE_MAX_AREA
    ):
        return False
    # Big backlog or still progressing — keep blocking new blueprints.
    return True


def _construction_summary(state: GameState) -> str:
    con = state.construction or {}
    instances = con.get("instances", 0)
    area = con.get("area", 0)
    return f"{instances} site(s), {area} tile(s)"


def _count_successful_build(message: str) -> None:
    msg = message.upper()
    if "CANTEEN" in msg or "EATERY" in msg:
        _session_build_counts["canteen"] = _session_build_counts.get("canteen", 0) + 1
    elif "HEARTH" in msg:
        _session_build_counts["hearth"] = _session_build_counts.get("hearth", 0) + 1
    elif "_HOME" in msg or " BUILT HOME" in msg:
        _session_build_counts["home"] = _session_build_counts.get("home", 0) + 1
    elif "WELL" in msg:
        _session_build_counts["well"] = _session_build_counts.get("well", 0) + 1
    elif "FARM" in msg:
        _session_build_counts["farm"] = _session_build_counts.get("farm", 0) + 1


def _is_home_target(target: str) -> bool:
    return any(t in target for t in HOME_TARGETS) or target.startswith("home")


def _is_hearth_target(target: str) -> bool:
    return any(t in target for t in HEARTH_TARGETS) or target.startswith("hearth")


def _is_canteen_target(target: str) -> bool:
    return any(t in target for t in CANTEEN_TARGETS) or target.startswith("canteen")


def _room_count(state: GameState, *keys: str, session_key: str | None = None) -> int:
    rc = state.roomCounts or {}
    for key in keys:
        if key in rc:
            try:
                return int(rc[key] or 0)
            except (TypeError, ValueError):
                pass
        # Case-insensitive contains match (mod may emit HOME / _CANTEEN etc.)
        needle = key.lower()
        for rk, rv in rc.items():
            if needle in str(rk).lower():
                try:
                    return int(rv or 0)
                except (TypeError, ValueError):
                    pass
    if session_key:
        return int(_session_build_counts.get(session_key, 0))
    return 0


def _home_count(state: GameState) -> int:
    return _room_count(state, "home", "_home", "HOME", session_key="home")


def _hearth_count(state: GameState) -> int:
    return _room_count(state, "hearth", "_hearth", "HEARTH", session_key="hearth")


def _canteen_count(state: GameState) -> int:
    return _room_count(
        state, "canteen", "_canteen", "CANTEEN", "eatery", session_key="canteen"
    )


def _finished_canteen_count(state: GameState) -> int:
    """Completed canteens only (roomCounts) — blueprints in session do not count."""
    rc = state.roomCounts or {}
    for key in ("canteen", "_canteen", "CANTEEN", "eatery"):
        if key in rc:
            try:
                return int(rc[key] or 0)
            except (TypeError, ValueError):
                pass
        needle = key.lower()
        for rk, rv in rc.items():
            if needle in str(rk).lower():
                try:
                    return int(rv or 0)
                except (TypeError, ValueError):
                    pass
    return 0


def _food_chain_ready(state: GameState) -> bool:
    """True once settlers can eat (finished canteen) or past early-game pop."""
    if _population(state) >= FOOD_READY_POP:
        return True
    return _finished_canteen_count(state) > 0


def _pantry_empty(state: GameState) -> bool:
    """True when no stockpile-stored goods (credits/meta keys ignored).

    Note: Songs of Syx only counts goods in stockpiles/haulers. Empty resources
    with farms+canteen usually means 'no stockpile yet', not 'no food production'.
    """
    res = state.resources or {}
    meta = {"credits", "food_days", "canteen_food", "stockpile_crates"}
    for key, val in res.items():
        if str(key).lower() in meta:
            continue
        try:
            if int(val or 0) > 0:
                return False
        except (TypeError, ValueError):
            continue
    return True


def _speed_cap(state: GameState) -> int:
    """Hard ceiling for set_speed. Daytime max is EARLY_SPEED_MAX (5x);
    overnight raises it via SYX_INJECT_SPEED=4."""
    return max(INJECTED_SPEED, EARLY_SPEED_MAX)


def _effective_inject_speed(state: GameState) -> int:
    """Speed we force when paused / construction-bound.

    Daytime INJECTED_SPEED=1 is fine when idle, but while blueprints are open
    (or food chain not finished) we must run at least EARLY_SPEED_MAX (5x) —
    otherwise sites never finish and stall logic falsely unblocks more builds.
    """
    if _construction_signature(state) is not None or not _food_chain_ready(state):
        return max(INJECTED_SPEED, EARLY_SPEED_MAX)
    return INJECTED_SPEED


def effective_inject_speed(state: GameState) -> int:
    """Public alias for bridge tick loops."""
    return _effective_inject_speed(state)


def _clamp_speed_command(cmd: Command, state: GameState) -> Command:
    """Rewrite set_speed so it never exceeds the daytime/overnight ceiling."""
    if cmd.action != "set_speed":
        return cmd
    cap = _speed_cap(state)
    params = dict(cmd.params or {})
    try:
        val = int(params.get("value", cap))
    except (TypeError, ValueError):
        val = cap
    if val > cap:
        params["value"] = cap
        return cmd.model_copy(update={"params": params})
    if "value" not in params:
        params["value"] = min(val, cap)
        return cmd.model_copy(update={"params": params})
    return cmd


def _farm_count(state: GameState) -> int:
    rc = state.roomCounts or {}
    for key in ("farm", "farm_grain", "FARM"):
        if key in rc:
            try:
                return int(rc[key])
            except (TypeError, ValueError):
                pass
    return _session_build_counts.get("farm", 0)


def _well_count(state: GameState) -> int:
    rc = state.roomCounts or {}
    for key in ("well", "well_normal", "WELL"):
        if key in rc:
            try:
                return int(rc[key])
            except (TypeError, ValueError):
                pass
    return _session_build_counts.get("well", 0)


def _game_needs_speed(state: GameState) -> bool:
    speed = state.gameSpeed or {}
    try:
        paused = float(speed.get("paused") or 0) > 0
        target = float(speed.get("target") if speed.get("target") is not None else 2)
        actual = float(speed.get("actual") if speed.get("actual") is not None else target)
    except (TypeError, ValueError):
        return False
    return paused or target < 1 or actual < 0.25


def apply_gameplay_adjustments(
    commands: list[Command],
    state: GameState,
) -> tuple[list[Command], str | None]:
    """When paused/slow or construction pending, prioritize set_speed over builds."""
    inject = _effective_inject_speed(state)
    builds = [c for c in commands if c.action == "build"]
    non_builds = [c for c in commands if c.action != "build"]

    if _construction_pending(state) and builds:
        speeds = [_clamp_speed_command(c, state) for c in non_builds if c.action == "set_speed"]
        note = (
            f"construction in progress ({_construction_summary(state)}) — "
            "set_speed only until finished"
        )
        if speeds:
            return speeds[:1], note
        return [Command(action="set_speed", params={"value": inject})], note

    if not _game_needs_speed(state):
        if len(builds) > 1:
            first_build = builds[0]
            rest = [_clamp_speed_command(c, state) for c in non_builds]
            return [first_build, *rest], "one build per tick — dropped extra builds"
        return [_clamp_speed_command(c, state) for c in commands], None
    if builds:
        return (
            [Command(action="set_speed", params={"value": inject})],
            f"game paused/slow — set_speed {inject} instead of build",
        )
    speeds = [_clamp_speed_command(c, state) for c in commands if c.action == "set_speed"]
    if speeds:
        return speeds[:1], None
    return (
        [Command(action="set_speed", params={"value": inject})],
        f"game paused — injecting set_speed {inject}",
    )


def _map_origin(state: GameState) -> tuple[int, int]:
    """World tile at mapRows[0][0]."""
    if state.mapFull and state.mapX2 >= state.mapX1:
        return state.mapX1, state.mapY1
    if state.mapRadius:
        return state.mapCenterX - state.mapRadius, state.mapCenterY - state.mapRadius
    return 0, 0


def _map_char_at(state: GameState, x: int, y: int) -> str | None:
    if not state.mapRows:
        return None
    ox, oy = _map_origin(state)
    col = x - ox
    row = y - oy
    if row < 0 or row >= len(state.mapRows):
        return None
    line = state.mapRows[row]
    if col < 0 or col >= len(line):
        return None
    return line[col]


def _has_forest_near_throne(state: GameState) -> bool:
    """True if mapRows shows ^ forest within build radius of throne."""
    tx, ty = _throne_xy(state)
    if tx is None or ty is None or not state.mapRows:
        return False
    ox, oy = _map_origin(state)
    for row_i, line in enumerate(state.mapRows):
        for col_i, ch in enumerate(line):
            if ch not in FOREST_TILE_CHARS:
                continue
            wx = ox + col_i
            wy = oy + row_i
            if _distance(wx, wy, tx, ty) <= MAX_THRONE_DISTANCE:
                return True
    return False


def _is_forest_build_site(state: GameState, x: int, y: int, reach: int = 2) -> bool:
    """Woodcutter needs trees at or near the requested coordinates."""
    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            ch = _map_char_at(state, x + dx, y + dy)
            if ch in FOREST_TILE_CHARS:
                return True
    return False


def _is_woodcutter_target(target: str) -> bool:
    return any(t in target for t in WOODCUTTER_TARGETS)


def _is_stockpile_target(target: str) -> bool:
    return any(t in target for t in STOCKPILE_TARGETS)


def _is_well_target(target: str) -> bool:
    return any(t in target for t in WELL_TARGETS) or target.startswith("well")


def _rewrite_build(cmd: Command) -> Command:
    """Route generic/cotton farms to food grain."""
    if cmd.action != "build":
        return cmd
    norm = _normalize_target(cmd.target)
    if norm == "farm" or norm in COTTON_FARM_MARKERS or ("farm" in norm and "cotton" in norm):
        return cmd.model_copy(update={"target": "farm_grain"})
    return cmd


def _normalize_target(target: str | None) -> str:
    if not target:
        return ""
    return re.sub(r"[^a-z0-9_]", "", target.lower())


def _population(state: GameState) -> int:
    try:
        return int(state.population.get("total", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _throne_xy(state: GameState) -> tuple[int | None, int | None]:
    if not state.throne:
        return None, None
    try:
        return int(state.throne.get("x")), int(state.throne.get("y"))
    except (TypeError, ValueError):
        return None, None


def _distance(x: int, y: int, tx: int, ty: int) -> float:
    return math.hypot(x - tx, y - ty)


def _footprint_gap_to_throne(
    x: int, y: int, w: int, h: int, tx: int, ty: int
) -> float:
    """Nearest distance from the throne to the build's WxH footprint at (x,y).

    0 when the throne sits inside the footprint. Used to keep an access ring
    clear around the throne rather than only measuring the build's origin.
    """
    near_x = min(max(tx, x), x + max(w, 1) - 1)
    near_y = min(max(ty, y), y + max(h, 1) - 1)
    return math.hypot(near_x - tx, near_y - ty)


def validate_command(
    cmd: Command,
    state: GameState,
    knowledge: OverlordKnowledge | None = None,
) -> tuple[bool, str | None]:
    """Return (allowed, rejection_reason). rejection_reason set when blocked."""
    if cmd.action != "build":
        return True, None

    if _construction_pending(state):
        return False, (
            f"construction in progress ({_construction_summary(state)}) — "
            "wait for settlers to finish; use set_speed only"
        )

    if _build_wait_ticks > 0:
        return False, (
            f"build wait ({_build_wait_ticks} bridge ticks left) — "
            "confirm current build finished before placing another"
        )

    target = _normalize_target(cmd.target)
    x, y = cmd.x, cmd.y

    if x is None or y is None:
        return False, "build requires x and y coordinates"

    if (x, y) in BAD_COORDS:
        tx, ty = _throne_xy(state)
        if tx is None or ty is None or _distance(x, y, tx, ty) > 5:
            return False, f"coordinates ({x},{y}) are invalid — build near throne"

    tx, ty = _throne_xy(state)
    if tx is not None and ty is not None:
        dist = _distance(x, y, tx, ty)
        if dist > MAX_THRONE_DISTANCE:
            return False, (
                f"({x},{y}) is {dist:.0f} tiles from throne ({tx},{ty}) "
                f"(max {MAX_THRONE_DISTANCE})"
            )
        w = int(cmd.params.get("width", 1) or 1)
        h = int(cmd.params.get("height", 1) or 1)
        gap = _footprint_gap_to_throne(x, y, w, h, tx, ty)
        if gap < MIN_THRONE_CLEARANCE:
            return False, (
                f"({x},{y}) {w}x{h} boxes in the throne ({tx},{ty}) — footprint "
                f"is {gap:.0f} tiles away, keep >= {MIN_THRONE_CLEARANCE} clear so "
                f"settlers can path. Build farther out on an open '.' tile."
            )

    if _farms_only:
        allowed = any(f in target for f in FARMS_ONLY_ALLOWED)
        if not allowed:
            return False, (
                "farms-only mode (TmpArea saturation) — only farm/pasture/orchard builds; "
                "use clear_placement or new game to reset"
            )

    if knowledge is not None:
        blocked, reason = knowledge.is_blocked(cmd.action, cmd.target, x, y)
        if blocked:
            return False, reason

    pop = _population(state)

    if _is_well_target(target) and _well_blocked_ticks > 0:
        return False, (
            f"well backoff ({_well_blocked_ticks} ticks left) after repeated TmpArea failures — "
            "build farm_grain or home instead"
        )

    if _is_home_target(target):
        homes = _home_count(state)
        if homes >= pop + HOME_HEADROOM:
            return False, (
                f"home headroom met ({homes} homes for pop {pop}, max pop+{HOME_HEADROOM}) — "
                "build farm_grain, wait for immigration, or set_speed 1"
            )
        if not _food_chain_ready(state) and _canteen_count(state) <= 0:
            return False, (
                "home blocked until canteen exists — settlers starve without a place to eat; "
                "build canteen next (ovens are placed inside it)"
            )
        # Need at least one farm before mass housing (canteen alone cooks nothing).
        if _farm_count(state) < 1:
            return False, (
                "home blocked — no farm yet; build farm_grain first so the canteen has food"
            )

    if _is_stockpile_target(target) and not _food_chain_ready(state) and pop < INDUSTRY_POP_THRESHOLD:
        return False, (
            f"stockpile blocked until canteen exists or pop >= {INDUSTRY_POP_THRESHOLD} "
            f"(current {pop}) — without a stockpile, harvest never shows in resources; "
            "finish farm+canteen first, then stockpile so grain can be stored"
        )

    if _is_woodcutter_target(target) and pop < INDUSTRY_POP_THRESHOLD:
        if not _has_forest_near_throne(state):
            return False, (
                f"woodcutter blocked until pop >= {INDUSTRY_POP_THRESHOLD} "
                f"(current {pop}) — no ^ forest tiles within {MAX_THRONE_DISTANCE} "
                "tiles of throne on mapRows; expand farms/homes"
            )
        if not _is_forest_build_site(state, x, y):
            return False, (
                f"woodcutter at ({x},{y}) has no ^ forest on mapRows nearby — "
                "pick coordinates on a ^ tile within "
                f"{MAX_THRONE_DISTANCE} of throne"
            )

    if pop < EARLY_GAME_POP_THRESHOLD and target in EARLY_GAME_BLOCKED:
        return False, (
            f"{cmd.target} blocked until population >= {EARLY_GAME_POP_THRESHOLD} "
            f"(current {pop}) — use farm, hearth, canteen, home, well"
        )

    return True, None


def filter_commands(
    commands: list[Command],
    state: GameState,
    knowledge: OverlordKnowledge | None = None,
) -> tuple[list[Command], list[tuple[Command, str]]]:
    """Split commands into allowed list and (cmd, reason) rejections."""
    allowed: list[Command] = []
    rejected: list[tuple[Command, str]] = []
    build_allowed = False
    for cmd in commands:
        cmd = _clamp_speed_command(_rewrite_build(cmd), state)
        if cmd.action == "build" and build_allowed:
            rejected.append((cmd, "one build per decision cycle — wait for current build to finish"))
            continue
        ok, reason = validate_command(cmd, state, knowledge)
        if ok:
            allowed.append(cmd)
            if cmd.action == "build":
                build_allowed = True
        elif reason:
            rejected.append((cmd, reason))
    return allowed, rejected


def apply_timeout_backoff(
    commands: list[Command],
    consecutive_timeouts: int,
    state: GameState | None = None,
) -> tuple[list[Command], bool]:
    """When game thread is saturated, only allow set_speed this tick."""
    if consecutive_timeouts < TIMEOUT_BACKOFF_THRESHOLD:
        return commands, False
    if state and _construction_pending(state):
        return [], True
    inject = _effective_inject_speed(state) if state else min(INJECTED_SPEED, EARLY_SPEED_MAX)
    speed = [_clamp_speed_command(c, state) if state else c for c in commands if c.action == "set_speed"]
    if speed:
        return speed[:1], True
    return [Command(action="set_speed", params={"value": inject})], True


def is_timeout_result(message: str) -> bool:
    return "timed out" in (message or "").lower()


def is_tmparea_result(message: str) -> bool:
    msg = (message or "").lower()
    return "tmparea" in msg.replace(" ", "") or "_home error" in msg
