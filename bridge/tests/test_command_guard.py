"""Tests for command_guard pre-flight validation."""
from __future__ import annotations

import unittest

from bridge.command_guard import (
    validate_command,
    apply_timeout_backoff,
    apply_gameplay_adjustments,
    filter_commands,
    is_timeout_result,
    record_build_outcome,
    reset_session_guard,
    _has_forest_near_throne,
)
from bridge.knowledge import OverlordKnowledge
from bridge.models import Command, GameState
from pathlib import Path
import tempfile


def _state(pop: int = 5, tx: int = 400, ty: int = 160) -> GameState:
    return GameState(
        population={"total": pop},
        throne={"x": tx, "y": ty},
    )


class CommandGuardTests(unittest.TestCase):
    def test_blocks_far_from_throne(self):
        cmd = Command(action="build", target="home", x=100, y=100)
        ok, reason = validate_command(cmd, _state())
        self.assertFalse(ok)
        self.assertIn("100", reason or "")

    def test_blocks_early_game_hunter(self):
        cmd = Command(action="build", target="hunter", x=410, y=160)
        ok, reason = validate_command(cmd, _state(pop=3))
        self.assertFalse(ok)
        self.assertIn("population", reason or "")

    def test_allows_farm_early(self):
        cmd = Command(action="build", target="farm", x=410, y=160)
        ok, _ = validate_command(cmd, _state(pop=3))
        self.assertTrue(ok)

    def test_blacklist_coord(self):
        with tempfile.TemporaryDirectory() as tmp:
            k = OverlordKnowledge(path=Path(tmp) / "k.json")
            k.record_failure(
                action="build", target="home", x=405, y=160,
                message="_HOME error TmpArea",
            )
            k.record_failure(
                action="build", target="home", x=405, y=160,
                message="_HOME error TmpArea",
            )
            cmd = Command(action="build", target="farm", x=405, y=160)
            ok, reason = validate_command(cmd, _state(), k)
            self.assertFalse(ok)
            self.assertIn("blacklisted", reason or "")

    def test_timeout_backoff(self):
        cmds = [
            Command(action="build", target="home", x=410, y=160),
            Command(action="set_speed", params={"value": 2}),
        ]
        out, backoff = apply_timeout_backoff(cmds, 3)
        self.assertTrue(backoff)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].action, "set_speed")

    def test_timeout_backoff_skips_during_construction(self):
        state = _state()
        state.construction = {"instances": 1, "area": 9}
        cmds = [Command(action="set_speed", params={"value": 2})]
        out, backoff = apply_timeout_backoff(cmds, 3, state)
        self.assertTrue(backoff)
        self.assertEqual(out, [])

    def test_is_timeout_result(self):
        self.assertTrue(is_timeout_result("Command timed out waiting for game thread"))

    def test_blocks_home_when_headroom_met(self):
        reset_session_guard()
        state = _state(pop=5)
        state.roomCounts = {"home": 8}
        cmd = Command(action="build", target="home", x=410, y=160)
        ok, reason = validate_command(cmd, state)
        self.assertFalse(ok)
        self.assertIn("headroom", reason or "")

    def test_apply_gameplay_adjustments_when_paused(self):
        state = _state()
        state.gameSpeed = {"paused": 1.0, "target": 0.0, "actual": 0.0}
        cmds = [Command(action="build", target="farm_grain", x=410, y=160)]
        out, note = apply_gameplay_adjustments(cmds, state)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].action, "set_speed")
        self.assertIn("set_speed", note or "")

    def test_blocks_build_when_construction_pending(self):
        state = _state()
        state.construction = {"instances": 1, "area": 4}
        cmd = Command(action="build", target="home", x=410, y=160)
        ok, reason = validate_command(cmd, state)
        self.assertFalse(ok)
        self.assertIn("construction in progress", reason or "")

    def test_apply_gameplay_strips_builds_when_construction_pending(self):
        state = _state()
        state.construction = {"instances": 2, "area": 8}
        cmds = [
            Command(action="build", target="farm_grain", x=410, y=160),
            Command(action="set_speed", params={"value": 2}),
        ]
        out, note = apply_gameplay_adjustments(cmds, state)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].action, "set_speed")
        self.assertIn("construction", note or "")

    def test_forest_near_throne_uses_map_full_origin(self):
        """mapFull exports index rows from mapX1/mapY1, not mapCenter - radius."""
        rows = ["." * 60 for _ in range(120)]
        row = list(rows[115])
        row[50] = "^"
        rows[115] = "".join(row)
        state = GameState(
            throne={"x": 120, "y": 180},
            mapRows=rows,
            mapRadius=40,
            mapCenterX=120,
            mapCenterY=180,
            mapFull=True,
            mapX1=50,
            mapY1=50,
            mapX2=109,
            mapY2=169,
        )
        self.assertTrue(_has_forest_near_throne(state))

    def test_forest_near_throne_false_without_forest_tiles(self):
        state = GameState(
            throne={"x": 120, "y": 180},
            mapRows=["." * 10 for _ in range(10)],
            mapRadius=40,
            mapCenterX=120,
            mapCenterY=180,
            mapFull=True,
            mapX1=50,
            mapY1=50,
            mapX2=59,
            mapY2=59,
        )
        self.assertFalse(_has_forest_near_throne(state))

    def test_blocks_canteen_without_hearth(self):
        """Canteen no longer requires a separate hearth room (ovens go inside)."""
        reset_session_guard()
        state = _state(pop=5)
        state.roomCounts = {"farm": 1}
        cmd = Command(action="build", target="canteen", x=410, y=160)
        ok, _ = validate_command(cmd, state)
        self.assertTrue(ok)

    def test_allows_canteen_with_hearth(self):
        reset_session_guard()
        state = _state(pop=5)
        state.roomCounts = {"farm": 1, "hearth": 1}
        cmd = Command(action="build", target="canteen", x=410, y=160)
        ok, _ = validate_command(cmd, state)
        self.assertTrue(ok)

    def test_blocks_home_until_canteen(self):
        reset_session_guard()
        state = _state(pop=5)
        state.roomCounts = {"farm": 1, "hearth": 1}
        cmd = Command(action="build", target="home", x=410, y=160)
        ok, reason = validate_command(cmd, state)
        self.assertFalse(ok)
        self.assertIn("canteen", reason or "")

    def test_allows_home_with_canteen(self):
        reset_session_guard()
        state = _state(pop=5)
        state.roomCounts = {"farm": 1, "hearth": 1, "canteen": 1}
        cmd = Command(action="build", target="home", x=410, y=160)
        ok, _ = validate_command(cmd, state)
        self.assertTrue(ok)

    def test_blocks_home_without_farm(self):
        reset_session_guard()
        state = _state(pop=5)
        state.roomCounts = {"canteen": 1}
        cmd = Command(action="build", target="home", x=410, y=160)
        ok, reason = validate_command(cmd, state)
        self.assertFalse(ok)
        self.assertIn("farm", reason or "")

    def test_allows_stockpile_with_canteen(self):
        reset_session_guard()
        state = _state(pop=10)
        state.roomCounts = {"farm": 1, "canteen": 1}
        cmd = Command(action="build", target="stockpile", x=410, y=160)
        ok, _ = validate_command(cmd, state)
        self.assertTrue(ok)

    def test_blocks_early_stockpile(self):
        reset_session_guard()
        state = _state(pop=5)
        cmd = Command(action="build", target="stockpile", x=410, y=160)
        ok, reason = validate_command(cmd, state)
        self.assertFalse(ok)
        self.assertIn("stockpile", reason or "")

    def test_early_inject_caps_set_speed(self):
        reset_session_guard()
        state = _state(pop=5)
        state.gameSpeed = {"paused": 1.0, "target": 0.0, "actual": 0.0}
        cmds = [Command(action="set_speed", params={"value": 4})]
        out, _ = apply_gameplay_adjustments(cmds, state)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].action, "set_speed")
        self.assertEqual(int(out[0].params.get("value", 99)), 2)

    def test_food_ready_idle_injects_daytime_speed(self):
        reset_session_guard()
        state = _state(pop=5)
        state.roomCounts = {"canteen": 1}
        state.gameSpeed = {"paused": 1.0, "target": 0.0, "actual": 0.0}
        cmds = [Command(action="build", target="farm", x=410, y=160)]
        out, note = apply_gameplay_adjustments(cmds, state)
        self.assertEqual(out[0].action, "set_speed")
        # Idle + finished canteen: daytime INJECTED_SPEED (default 1)
        self.assertEqual(int(out[0].params.get("value", 99)), 1)
        self.assertIn("set_speed", note or "")

    def test_construction_forces_builder_speed_even_with_canteen(self):
        """Regression: canteen blueprint/finished must not drop inject to 1x
        while sites are still open — that froze the 30m playtest."""
        reset_session_guard()
        state = _state(pop=9)
        state.roomCounts = {"canteen": 1, "farm": 1}
        state.construction = {"instances": 12, "area": 200}
        state.gameSpeed = {"paused": 0.0, "target": 1.0, "actual": 1.0}
        cmds = [
            Command(action="build", target="home", x=420, y=160),
            Command(action="set_speed", params={"value": 2}),
        ]
        out, note = apply_gameplay_adjustments(cmds, state)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].action, "set_speed")
        self.assertEqual(int(out[0].params.get("value", 99)), 2)
        self.assertIn("construction", note or "")
        ok, reason = validate_command(
            Command(action="build", target="home", x=420, y=160), state
        )
        self.assertFalse(ok)
        self.assertIn("construction", reason or "")

    def test_llm_set_speed_2_not_clamped_after_canteen(self):
        reset_session_guard()
        state = _state(pop=9)
        state.roomCounts = {"canteen": 1}
        state.gameSpeed = {"paused": 0.0, "target": 1.0, "actual": 1.0}
        cmds = [Command(action="set_speed", params={"value": 2})]
        out, _ = apply_gameplay_adjustments(cmds, state)
        self.assertEqual(int(out[0].params.get("value", 99)), 2)

    def test_large_stalled_backlog_still_blocks_builds(self):
        from bridge import command_guard as cg

        reset_session_guard()
        state = _state(pop=9)
        state.construction = {"instances": 15, "area": 299}
        # Simulate stall past threshold without shrinking the backlog
        cg._construction_sig = (15, 299)
        cg._construction_stall_ticks = cg.CONSTRUCTION_STALL_TICKS + 2
        ok, reason = validate_command(
            Command(action="build", target="home", x=420, y=160), state
        )
        self.assertFalse(ok)
        self.assertIn("construction", reason or "")


if __name__ == "__main__":
    unittest.main()
