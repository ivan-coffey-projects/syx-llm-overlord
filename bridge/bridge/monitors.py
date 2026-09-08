"""Game monitor selection — GLFW MONITOR index ↔ XRandR output."""
from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PERSONAL_ROOT = Path.home() / ".config" / "syx-llm-overlord"
DEFAULT_LAUNCHER_SETTINGS = Path.home() / ".local/share/songsofsyx/settings/LauncherSettings.txt"

MONITOR_PROFILES: tuple[dict, ...] = (
    {"index": 0, "label": "Display 1", "xrandr": "DP-1", "aliases": ("primary", "display-1", "dp-1")},
    {"index": 1, "label": "Display 2", "xrandr": "DP-2", "aliases": ("display-2", "dp-2")},
    {"index": 2, "label": "Display 3", "xrandr": "HDMI-1", "aliases": ("display-3", "hdmi-1")},
)


@dataclass
class MonitorInfo:
    index: int
    label: str
    xrandr: str
    connected: bool
    geometry: str | None
    width: int | None
    height: int | None
    x: int | None
    y: int | None
    active: bool


def personal_root() -> Path:
    return Path(os.environ.get("SYX_PERSONAL_ROOT", DEFAULT_PERSONAL_ROOT))


def launcher_settings_path() -> Path:
    return Path(os.environ.get("SYX_LAUNCHER_SETTINGS", DEFAULT_LAUNCHER_SETTINGS))


def launch_conf_path() -> Path:
    return personal_root() / "syx.launch.conf"


def _xrandr_works(display: str) -> bool:
    try:
        proc = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=3,
            env={**os.environ, "DISPLAY": display},
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if proc.returncode != 0:
        return False
    return " connected" in proc.stdout


def resolve_display() -> str:
    """Pick an XWayland display that can run xrandr (Wayland sessions often use :0)."""
    current = os.environ.get("DISPLAY", "").strip()
    if current and _xrandr_works(current):
        return current
    for candidate in (":0", ":1"):
        if candidate != current and _xrandr_works(candidate):
            return candidate
    return current or ":0"


def display_env() -> dict[str, str]:
    env = os.environ.copy()
    env["DISPLAY"] = resolve_display()
    return env


def _xrandr_outputs() -> dict[str, dict[str, int | str]]:
    """Parse connected outputs from xrandr --query."""
    outputs: dict[str, dict[str, int | str]] = {}
    try:
        proc = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=5,
            env=display_env(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return outputs

    geo_re = re.compile(r"^(\d+)x(\d+)\+(\d+)\+(\d+)$")
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2 or parts[1] != "connected":
            continue
        name = parts[0]
        geom: dict[str, int | str] = {"connected": True}
        for token in parts[2:]:
            m = geo_re.match(token)
            if m:
                geom["width"] = int(m.group(1))
                geom["height"] = int(m.group(2))
                geom["x"] = int(m.group(3))
                geom["y"] = int(m.group(4))
                geom["geometry"] = token
                break
        outputs[name] = geom
    return outputs


def read_launcher_monitor_index() -> int | None:
    path = launcher_settings_path()
    if not path.is_file():
        return None
    for line in path.read_text().splitlines():
        m = re.match(r"^\s*MONITOR:\s*(\d+)\s*,?\s*$", line.strip())
        if m:
            idx = int(m.group(1))
            if 0 <= idx <= 2:
                return idx
    return None


def read_launch_conf_monitor_index() -> int | None:
    path = launch_conf_path()
    if not path.is_file():
        return None
    for line in path.read_text().splitlines():
        m = re.match(r'^\s*export\s+SYX_MONITOR_INDEX=(\d+)\s*$', line)
        if m:
            return int(m.group(1))
    return None


def active_monitor_index() -> int:
    idx = read_launcher_monitor_index()
    if idx is not None:
        return idx
    idx = read_launch_conf_monitor_index()
    if idx is not None:
        return idx
    return 0


def xrandr_for_index(index: int) -> str:
    for profile in MONITOR_PROFILES:
        if profile["index"] == index:
            return str(profile["xrandr"])
    raise ValueError(f"invalid monitor index: {index}")


def list_monitors() -> list[MonitorInfo]:
    active = active_monitor_index()
    xrandr = _xrandr_outputs()
    result: list[MonitorInfo] = []
    for profile in MONITOR_PROFILES:
        idx = int(profile["index"])
        out = str(profile["xrandr"])
        info = xrandr.get(out, {})
        connected = bool(info.get("connected"))
        result.append(
            MonitorInfo(
                index=idx,
                label=str(profile["label"]),
                xrandr=out,
                connected=connected,
                geometry=str(info["geometry"]) if info.get("geometry") else None,
                width=int(info["width"]) if info.get("width") is not None else None,
                height=int(info["height"]) if info.get("height") is not None else None,
                x=int(info["x"]) if info.get("x") is not None else None,
                y=int(info["y"]) if info.get("y") is not None else None,
                active=idx == active,
            )
        )
    return result


def _rewrite_launcher_settings(index: int) -> None:
    path = launcher_settings_path()
    if not path.is_file():
        raise FileNotFoundError(str(path))
    lines = path.read_text().splitlines(keepends=True)
    replaced = False
    out: list[str] = []
    for line in lines:
        if re.match(r"^\s*MONITOR:\s*\d+", line):
            out.append(f"MONITOR: {index},\n")
            replaced = True
        else:
            out.append(line if line.endswith("\n") else line + "\n")
    if not replaced:
        raise ValueError("MONITOR line not found in LauncherSettings.txt")
    path.write_text("".join(out))


def _rewrite_launch_conf(index: int, xrandr: str) -> None:
    path = launch_conf_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text() if path.is_file() else ""
    lines = text.splitlines()
    idx_line = f"export SYX_MONITOR_INDEX={index}"
    out_line = f'export SYX_XRANDR_OUTPUT="{xrandr}"'
    found_idx = found_out = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith("export SYX_MONITOR_INDEX="):
            new_lines.append(idx_line)
            found_idx = True
        elif line.startswith("export SYX_XRANDR_OUTPUT="):
            new_lines.append(out_line)
            found_out = True
        else:
            new_lines.append(line)
    if not found_idx:
        new_lines.append(idx_line)
    if not found_out:
        new_lines.append(out_line)
    path.write_text("\n".join(new_lines).rstrip() + "\n")


def find_game_window_id() -> str | None:
    env = display_env()
    patterns = ("Songs of Syx", "SOS Launcher", "Songs")
    for pattern in patterns:
        try:
            proc = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name", pattern],
                capture_output=True,
                text=True,
                timeout=5,
                env=env,
            )
            for line in proc.stdout.splitlines():
                wid = line.strip()
                if wid.isdigit():
                    return wid
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


def pin_game_window(index: int | None = None) -> dict:
    """Move the game window onto the target monitor (move-only, no resize)."""
    idx = index if index is not None else active_monitor_index()
    monitors = {m.index: m for m in list_monitors()}
    mon = monitors.get(idx)
    if not mon:
        return {"success": False, "message": f"Unknown monitor index {idx}"}
    if not mon.connected or mon.x is None or mon.y is None:
        return {"success": False, "message": f"{mon.xrandr} is not connected"}

    wid = find_game_window_id()
    if not wid:
        return {"success": False, "message": "Game window not found (is the game running?)"}

    env = display_env()
    try:
        subprocess.run(
            ["xdotool", "windowmove", wid, str(mon.x), str(mon.y)],
            check=True,
            capture_output=True,
            timeout=5,
            env=env,
        )
        subprocess.run(
            ["xdotool", "windowraise", wid],
            capture_output=True,
            timeout=5,
            env=env,
        )
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
        return {"success": False, "message": str(e)}

    logger.info(f"Pinned window {wid} to monitor {idx} ({mon.xrandr}) at {mon.x},{mon.y}")
    return {
        "success": True,
        "message": f"Moved game window to {mon.label} ({mon.xrandr})",
        "window_id": wid,
        "monitor_index": idx,
        "xrandr": mon.xrandr,
    }


def apply_monitor(index: int, *, pin_now: bool = True) -> dict:
    if index not in (0, 1, 2):
        return {"success": False, "message": "Monitor index must be 0, 1, or 2"}

    xrandr = xrandr_for_index(index)
    try:
        _rewrite_launcher_settings(index)
        _rewrite_launch_conf(index, xrandr)
    except (OSError, ValueError) as e:
        return {"success": False, "message": str(e)}

    pin_result: dict | None = None
    if pin_now:
        pin_result = pin_game_window(index)

    return {
        "success": True,
        "message": f"Monitor set to {index} ({xrandr})",
        "monitor_index": index,
        "xrandr": xrandr,
        "launcher_settings": str(launcher_settings_path()),
        "launch_conf": str(launch_conf_path()),
        "pin": pin_result,
    }
