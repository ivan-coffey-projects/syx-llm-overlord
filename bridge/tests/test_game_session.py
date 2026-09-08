"""Tests for GameSessionTracker new-game detection."""
from __future__ import annotations

import unittest

from bridge.game_session import GameSessionTracker
from bridge.models import GameState


def _state(day: int, year: int = 0, tx: int = 621, ty: int = 481) -> GameState:
    return GameState(
        population={"total": 9},
        throne={"x": tx, "y": ty},
        gameTime={"day": day, "year": year, "hour": 12},
    )


class GameSessionTests(unittest.TestCase):
    def test_year_rollover_is_not_new_game(self):
        t = GameSessionTracker()
        self.assertFalse(t.check_new_game(_state(day=14, year=0)))
        self.assertFalse(t.check_new_game(_state(day=15, year=0)))
        # Calendar wraps — used to false-trigger and wipe session builds
        self.assertFalse(t.check_new_game(_state(day=0, year=1)))

    def test_throne_move_is_new_game(self):
        t = GameSessionTracker()
        self.assertFalse(t.check_new_game(_state(day=5, year=0, tx=621, ty=481)))
        self.assertTrue(t.check_new_game(_state(day=0, year=0, tx=100, ty=200)))

    def test_day_reset_same_year_is_new_game(self):
        t = GameSessionTracker()
        self.assertFalse(t.check_new_game(_state(day=10, year=0)))
        self.assertTrue(t.check_new_game(_state(day=0, year=0)))


if __name__ == "__main__":
    unittest.main()
