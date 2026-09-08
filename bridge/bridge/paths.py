"""Resolve project paths from repo root and optional env overrides."""
from __future__ import annotations

import os
from pathlib import Path

# Repo root: syx-llm-overlord/ (parent of bridge/)
REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return Path(os.environ.get("SYX_OVERLORD_ROOT", REPO_ROOT))


def logs_dir() -> Path:
    return Path(os.environ.get("SYX_OVERLORD_LOGS", repo_root() / "logs"))


def memory_path() -> Path:
    return Path(os.environ.get("SYX_MEMORY_PATH", logs_dir() / "overlord-memory.jsonl"))


def wiki_dir() -> Path:
    return Path(os.environ.get("SYX_WIKI_DIR", repo_root() / "wiki"))


def playbook_path() -> Path:
    return Path(
        os.environ.get(
            "SYX_PLAYBOOK_PATH",
            wiki_dir() / "rules" / "playbook.md",
        )
    )


def memory_wiki_path() -> Path:
    return Path(
        os.environ.get(
            "SYX_MEMORY_WIKI_PATH",
            wiki_dir() / "memory" / "live-log.md",
        )
    )


def knowledge_path() -> Path:
    return Path(os.environ.get("SYX_KNOWLEDGE_PATH", logs_dir() / "overlord-knowledge.json"))


def map_pins_path() -> Path:
    return Path(os.environ.get("SYX_MAP_PINS_PATH", logs_dir() / "map-pins.json"))


def knowledge_wiki_path() -> Path:
    return Path(
        os.environ.get(
            "SYX_KNOWLEDGE_WIKI_PATH",
            wiki_dir() / "memory" / "knowledge.md",
        )
    )


def screenshots_dir() -> Path:
    return Path(os.environ.get("SYX_SCREENSHOTS_DIR", logs_dir() / "screenshots"))


def restart_script_path() -> Path:
    if os.environ.get("SYX_RESTART_SCRIPT"):
        return Path(os.environ["SYX_RESTART_SCRIPT"])
    return repo_root() / "scripts" / "restart-game-only.sh"


def game_dir() -> Path | None:
    raw = os.environ.get("SONGSOFSYX_DIR") or os.environ.get("SONGSOFSYX_GAME_DIR")
    return Path(raw) if raw else None


def game_jar_path() -> Path | None:
    raw = os.environ.get("SONGSOFSYX_JAR")
    if raw:
        return Path(raw)
    gd = game_dir()
    if gd and (gd / "SongsOfSyx.jar").is_file():
        return gd / "SongsOfSyx.jar"
    return None
