"""Capture the Songs of Syx game window for LLM vision."""
from __future__ import annotations

import base64
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .paths import screenshots_dir

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_PATTERNS = (
    "Songs of Syx",
    "SOS Launcher",
    "Songs",
)


@dataclass
class ScreenshotResult:
    ok: bool
    path: Path | None = None
    base64_png: str | None = None
    width: int | None = None
    height: int | None = None
    window_id: str | None = None
    error: str | None = None


def _display_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    env.setdefault("XDG_SESSION_TYPE", "x11")
    return env


def _tool(name: str) -> str | None:
    return shutil.which(name)


def find_game_window_id(patterns: tuple[str, ...] | None = None) -> str | None:
    """Return X11 window id for the game (xdotool)."""
    if _tool("xdotool") is None:
        return None
    patterns = patterns or DEFAULT_WINDOW_PATTERNS
    env = _display_env()
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
        except (subprocess.TimeoutExpired, OSError):
            continue
    return None


def _resize_png(path: Path, max_width: int) -> None:
    convert = _tool("magick") or _tool("convert")
    if convert is None or max_width <= 0:
        return
    tmp = path.with_suffix(".tmp.png")
    try:
        subprocess.run(
            [convert, str(path), "-resize", f"{max_width}x{max_width}>", str(tmp)],
            check=True,
            capture_output=True,
            timeout=15,
            env=_display_env(),
        )
        tmp.replace(path)
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def _image_size(path: Path) -> tuple[int | None, int | None]:
    magick = _tool("magick")
    identify = _tool("identify")
    if magick:
        cmd = [magick, "identify", "-format", "%w %h", str(path)]
    elif identify:
        cmd = [identify, "-format", "%w %h", str(path)]
    else:
        return None, None
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        parts = proc.stdout.strip().split()
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except (ValueError, OSError, subprocess.TimeoutExpired):
        pass
    return None, None


def capture_game_screenshot(
    *,
    dest: Path | None = None,
    max_width: int = 1024,
    window_patterns: tuple[str, ...] | None = None,
) -> ScreenshotResult:
    """
    Grab a PNG of the game window via xdotool + ImageMagick import.

    Requires X11 tools: xdotool, import (ImageMagick). Falls back gracefully.
    """
    if _tool("import") is None:
        return ScreenshotResult(ok=False, error="ImageMagick import not installed")

    wid = find_game_window_id(window_patterns)
    if not wid:
        return ScreenshotResult(ok=False, error="game window not found (xdotool)")

    out_dir = screenshots_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    if dest is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        dest = out_dir / f"settlement-{stamp}.png"
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)

    env = _display_env()
    try:
        # NOTE: do NOT `xdotool windowactivate` here — it raises the game window
        # and steals keyboard focus from whatever the user is typing. The game
        # window is fullscreen and unoccluded on its own monitor, so `import
        # -window` can grab it directly without activation.
        subprocess.run(
            ["import", "-window", wid, str(dest)],
            check=True,
            capture_output=True,
            timeout=15,
            env=env,
        )
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
        return ScreenshotResult(ok=False, window_id=wid, error=str(e))

    if not dest.is_file() or dest.stat().st_size == 0:
        return ScreenshotResult(ok=False, window_id=wid, error="capture produced empty file")

    _resize_png(dest, max_width)
    w, h = _image_size(dest)
    try:
        b64 = base64.standard_b64encode(dest.read_bytes()).decode("ascii")
    except OSError as e:
        return ScreenshotResult(ok=False, path=dest, window_id=wid, error=str(e))

    logger.info(f"Screenshot captured: {dest} ({w}x{h}) window={wid}")
    _prune_screenshots(out_dir)
    return ScreenshotResult(
        ok=True,
        path=dest,
        base64_png=b64,
        width=w,
        height=h,
        window_id=wid,
    )


# A live viewer (the pitch deck's porthole, the dashboard) captures every
# ~2s, which banks gigabytes overnight if nobody sweeps the floor. Keep a
# sitting's worth of history; only the auto-stamped files are fair game.
SCREENSHOT_KEEP = 300


def _prune_screenshots(d: Path, keep: int = SCREENSHOT_KEEP) -> None:
    try:
        files = sorted(d.glob("settlement-*.png"), key=lambda p: p.stat().st_mtime)
        for stale in files[:-keep]:
            stale.unlink(missing_ok=True)
    except OSError as e:
        logger.debug(f"screenshot prune skipped: {e}")


def latest_screenshot_path() -> Path | None:
    """Most recent PNG in the screenshots directory."""
    d = screenshots_dir()
    if not d.is_dir():
        return None
    files = sorted(d.glob("*.png"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def save_uploaded_screenshot(
    data: bytes,
    filename: str = "upload.png",
    *,
    max_width: int = 1024,
) -> ScreenshotResult:
    """Save uploaded image bytes for LLM vision (chat or tick)."""
    if not data:
        return ScreenshotResult(ok=False, error="empty upload")

    ext = Path(filename).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        ext = ".png"

    out_dir = screenshots_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = out_dir / f"upload-{stamp}{ext}"

    try:
        dest.write_bytes(data)
    except OSError as e:
        return ScreenshotResult(ok=False, error=str(e))

    if ext != ".png" and (_tool("magick") or _tool("convert")):
        png_dest = dest.with_suffix(".png")
        convert = _tool("magick") or _tool("convert")
        try:
            subprocess.run(
                [convert, str(dest), str(png_dest)],
                check=True,
                capture_output=True,
                timeout=15,
            )
            dest.unlink(missing_ok=True)
            dest = png_dest
        except (subprocess.CalledProcessError, OSError):
            pass

    _resize_png(dest, max_width)
    w, h = _image_size(dest)
    try:
        b64 = base64.standard_b64encode(dest.read_bytes()).decode("ascii")
    except OSError as e:
        return ScreenshotResult(ok=False, path=dest, error=str(e))

    logger.info(f"Screenshot uploaded: {dest} ({w}x{h})")
    return ScreenshotResult(
        ok=True,
        path=dest,
        base64_png=b64,
        width=w,
        height=h,
    )
