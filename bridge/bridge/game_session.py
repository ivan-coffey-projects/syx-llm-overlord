"""Detect new Songs of Syx saves so memory/knowledge reset per settlement."""
from __future__ import annotations

from .models import GameState


class GameSessionTracker:
    """Track throne/day/year signature; fire when the player starts a new game."""

    def __init__(self) -> None:
        self._last_throne: tuple[int | None, int | None] | None = None
        self._last_day: int | None = None
        self._last_year: int | None = None
        self._initialized = False

    @staticmethod
    def _throne_xy(state: GameState) -> tuple[int | None, int | None]:
        if not state.throne:
            return None, None
        try:
            return int(state.throne.get("x")), int(state.throne.get("y"))
        except (TypeError, ValueError):
            return None, None

    @staticmethod
    def _day(state: GameState) -> int | None:
        if not state.gameTime:
            return None
        try:
            return int(state.gameTime.get("day", 0))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _year(state: GameState) -> int | None:
        if not state.gameTime:
            return None
        try:
            return int(state.gameTime.get("year", 0))
        except (TypeError, ValueError):
            return None

    def check_new_game(self, state: GameState) -> bool:
        """Return True once when we detect a new settlement / rolled-back save.

        Year rollover (day 15→0, year N→N+1) is NOT a new game — that used to
        wipe session canteen/home counts mid-colony and unlock bad builds.
        """
        throne = self._throne_xy(state)
        day = self._day(state)
        year = self._year(state)

        if not self._initialized:
            self._initialized = True
            self._last_throne = throne
            self._last_day = day
            self._last_year = year
            return False

        if throne[0] is not None and self._last_throne != throne:
            self._last_throne = throne
            self._last_day = day
            self._last_year = year
            return True

        # Same throne, day dropped hard — only new game if year did not advance
        # (year+1 + day reset = calendar rollover; year same/lower = reload/new).
        if (
            day is not None
            and self._last_day is not None
            and day <= 1
            and self._last_day >= 3
        ):
            year_advanced = (
                year is not None
                and self._last_year is not None
                and year > self._last_year
            )
            self._last_throne = throne
            self._last_day = day
            self._last_year = year
            if year_advanced:
                return False
            return True

        self._last_throne = throne
        self._last_day = day
        self._last_year = year
        return False
