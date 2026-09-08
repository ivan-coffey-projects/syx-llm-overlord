"""Tests for LLM state map stripping."""
from __future__ import annotations

import unittest

from bridge.models import GameState, state_for_llm


class MapStateTests(unittest.TestCase):
    def test_state_for_llm_strips_map_when_disabled(self):
        state = GameState(
            throne={"x": 100, "y": 200},
            mapRows=["..T.."],
            mapRadius=2,
            mapFull=True,
            mapX1=98,
            mapY1=198,
            mapX2=102,
            mapY2=202,
        )
        data = state_for_llm(state, include_map=False)
        self.assertNotIn("mapRows", data)
        self.assertNotIn("mapRadius", data)
        self.assertIn("throne", data)

    def test_summarize_without_map(self):
        state = GameState(throne={"x": 1, "y": 2}, mapRows=["T"], mapRadius=0)
        text = state.summarize(include_map=False)
        self.assertIn("Tile map: OFF", text)
        self.assertNotIn("Tile map (", text)


if __name__ == "__main__":
    unittest.main()
