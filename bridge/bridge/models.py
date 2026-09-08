"""Pydantic models for game state, commands, and LLM decisions."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime

from .map_constants import MAX_THRONE_DISTANCE


class GameState(BaseModel):
    """Snapshot of the game state from the mod API."""
    timestamp: int = 0
    population: dict[str, Any] = Field(default_factory=dict)
    resources: dict[str, Any] = Field(default_factory=dict)
    happiness: dict[str, Any] = Field(default_factory=dict)
    roomCounts: dict[str, Any] = Field(default_factory=dict)
    construction: dict[str, Any] = Field(default_factory=dict)
    military: dict[str, Any] = Field(default_factory=dict)
    diplomacy: dict[str, Any] = Field(default_factory=dict)
    gameTime: dict[str, Any] = Field(default_factory=dict)
    gameSpeed: dict[str, Any] = Field(default_factory=dict)
    throne: dict[str, Any] = Field(default_factory=dict)
    mapCenterX: int = 0
    mapCenterY: int = 0
    mapRadius: int = 0
    mapFull: bool = False
    mapX1: int = 0
    mapY1: int = 0
    mapX2: int = 0
    mapY2: int = 0
    mapLegend: str = ""
    mapRows: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def summarize(self, *, include_map: bool = True) -> str:
        """Human-readable summary for LLM prompts."""
        parts = []
        if self.gameTime:
            parts.append(f"Day {self.gameTime.get('day', '?')}, Year {self.gameTime.get('year', '?')}")
        if self.throne:
            parts.append(
                f"Throne at ({self.throne.get('x', '?')}, {self.throne.get('y', '?')}) "
                f"— build within ~{MAX_THRONE_DISTANCE} tiles"
            )
        if include_map and self.mapRows and self.mapRadius:
            parts.append(self._map_summary())
        elif not include_map:
            parts.append(
                "Tile map: OFF for Overlord prompts (partial grids confuse placement). "
                f"Use throne coords, roomCounts, construction, memory, and player map pins. "
                f"Spread builds across open ground {MAX_THRONE_DISTANCE} tiles from throne."
            )
        if self.population:
            parts.append(f"Population: {self.population.get('total', 'unknown')}")
        if self.happiness:
            overall = self.happiness.get('overall', 'unknown')
            parts.append(f"Happiness: {overall}")
        if self.resources:
            top_resources = list(self.resources.items())[:10]
            res_str = ", ".join(f"{k}: {v}" for k, v in top_resources)
            parts.append(f"Resources: {res_str}")
        if self.roomCounts:
            parts.append(f"Rooms: {self.roomCounts}")
        if self.construction:
            inst = self.construction.get("instances", 0)
            area = self.construction.get("area", 0)
            if inst or area:
                parts.append(
                    f"Construction in progress: {inst} site(s), {area} tile(s) — "
                    "do NOT place new builds until finished"
                )
            else:
                parts.append("Construction: none pending")
        if self.military:
            parts.append(f"Military: {self.military}")
        if self.diplomacy:
            parts.append(f"Diplomacy: {self.diplomacy}")
        if self.errors:
            parts.append(f"State errors: {', '.join(self.errors)}")
        return "\n".join(parts) if parts else "No state data available"

    def _map_summary(self) -> str:
        legend = self.mapLegend or "T=throne +=room .=open ~=water ^=forest X=blocked"
        if self.mapFull and self.mapX2 >= self.mapX1 and self.mapY2 >= self.mapY1:
            w = self.mapX2 - self.mapX1 + 1
            h = self.mapY2 - self.mapY1 + 1
            header = (
                f"Tile map (FULL settlement {w}×{h}, "
                f"bounds x={self.mapX1}..{self.mapX2} y={self.mapY1}..{self.mapY2}, "
                f"throne {self.mapCenterX},{self.mapCenterY}):"
            )
        else:
            header = (
                f"Tile map ({self.mapRadius} tiles radius, center {self.mapCenterX},{self.mapCenterY}):"
            )
        lines = [header, f"Legend: {legend}"]
        lines.extend(self.mapRows)
        return "\n".join(lines)


MAP_STATE_KEYS = (
    "mapRows",
    "mapLegend",
    "mapCenterX",
    "mapCenterY",
    "mapRadius",
    "mapFull",
    "mapX1",
    "mapY1",
    "mapX2",
    "mapY2",
)


def state_for_llm(state: GameState, *, include_map: bool) -> dict[str, Any]:
    """Drop map grid from JSON sent to the LLM when map.llm_enabled is false."""
    data = state.model_dump()
    if not include_map:
        for key in MAP_STATE_KEYS:
            data.pop(key, None)
    return data


class Command(BaseModel):
    """A command to execute in the game."""
    action: str
    target: str | None = None
    x: int | None = None
    y: int | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class CommandResult(BaseModel):
    """Result of executing a command."""
    success: bool
    message: str


class LLMDecision(BaseModel):
    """A structured decision from the LLM."""
    reasoning: str
    mood: str = "neutral"
    commands: list[Command] = Field(default_factory=list)


class TickRecord(BaseModel):
    """Record of one decision cycle."""
    tick_number: int
    timestamp: datetime = Field(default_factory=datetime.now)
    game_state: GameState
    llm_decision: LLMDecision | None = None
    command_results: list[CommandResult] = Field(default_factory=list)
    error: str | None = None
