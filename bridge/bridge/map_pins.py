"""Player-placed map pins — coordinates the LLM should build at."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .paths import map_pins_path

PIN_TYPES = ("farm", "home", "well", "stockpile", "woodcutter", "custom")

TYPE_COLORS = {
    "farm": "#4caf50",
    "home": "#ff9800",
    "well": "#29b6f6",
    "stockpile": "#8d6e63",
    "woodcutter": "#795548",
    "custom": "#e91e63",
}


@dataclass
class MapPin:
    id: str
    x: int
    y: int
    label: str
    pin_type: str = "custom"
    color: str = "#e91e63"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def order_line(self) -> str:
        if self.pin_type and self.pin_type != "custom":
            return f"Build {self.pin_type} at ({self.x},{self.y}) — {self.label}"
        return f"Build at ({self.x},{self.y}) — {self.label}"


class MapPinStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or map_pins_path()
        self._pins: list[MapPin] = []
        self.load()

    def load(self) -> None:
        self._pins = []
        if not self.path.is_file():
            return
        try:
            raw = json.loads(self.path.read_text())
            for item in raw if isinstance(raw, list) else []:
                self._pins.append(
                    MapPin(
                        id=str(item.get("id", uuid.uuid4())),
                        x=int(item["x"]),
                        y=int(item["y"]),
                        label=str(item.get("label", "build here")),
                        pin_type=str(item.get("pin_type", "custom")),
                        color=str(item.get("color", TYPE_COLORS.get(item.get("pin_type", "custom"), "#e91e63"))),
                    )
                )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            self._pins = []

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([p.to_dict() for p in self._pins], indent=2))

    def list(self) -> list[MapPin]:
        return list(self._pins)

    def snapshot(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._pins]

    def get(self, pin_id: str) -> MapPin | None:
        for p in self._pins:
            if p.id == pin_id:
                return p
        return None

    def add(
        self,
        x: int,
        y: int,
        label: str = "build here",
        pin_type: str = "custom",
        color: str | None = None,
    ) -> MapPin:
        pin_type = pin_type if pin_type in PIN_TYPES else "custom"
        pin = MapPin(
            id=str(uuid.uuid4()),
            x=int(x),
            y=int(y),
            label=(label or "build here").strip()[:120],
            pin_type=pin_type,
            color=color or TYPE_COLORS.get(pin_type, "#e91e63"),
        )
        self._pins.append(pin)
        self.save()
        return pin

    def remove(self, pin_id: str) -> bool:
        before = len(self._pins)
        self._pins = [p for p in self._pins if p.id != pin_id]
        if len(self._pins) < before:
            self.save()
            return True
        return False

    def remove_at(self, x: int, y: int) -> bool:
        before = len(self._pins)
        self._pins = [p for p in self._pins if not (p.x == x and p.y == y)]
        if len(self._pins) < before:
            self.save()
            return True
        return False

    def clear(self) -> None:
        self._pins = []
        self.save()

    def for_prompt(self) -> str:
        if not self._pins:
            return ""
        lines = ["PLAYER MAP PINS (priority build locations — use exact x,y):"]
        for p in self._pins:
            lines.append(f"- ({p.x},{p.y}): {p.pin_type} — {p.label}")
        return "\n".join(lines)

    def queue_lines(self) -> list[str]:
        return [p.order_line() for p in self._pins]
