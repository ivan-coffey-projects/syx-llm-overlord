"""Configuration loader for the bridge service."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .personalities import (
    DEFAULT_PERSONA,
    DEFAULT_GAME_MODE,
    DEFAULT_PERSONALITY,
    normalize_persona_id,
    normalize_game_mode_id,
    normalize_personality_id,
    resolve_overlord_settings,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
USER_ENV_PATH = Path(
    os.environ.get(
        "SYX_USER_ENV",
        Path.home() / ".config" / "syx-llm-overlord" / ".env",
    )
)
_ENV_LOADED = False


def _load_env_files() -> None:
    """Load repo and user env files without overriding existing variables."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    repo_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(repo_root / ".env", override=False)
    load_dotenv(USER_ENV_PATH, override=False)
    _ENV_LOADED = True


DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
DEFAULT_OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_FREE_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
DEFAULT_OPENROUTER_FALLBACK = os.environ.get(
    "SYX_LLM_FALLBACK_MODEL", "google/gemma-4-26b-a4b-it:free"
)

# Free via OpenRouter preview / $0 pricing but no :free suffix (may be absent from /models API)
OPENROUTER_FREE_ALLOWLIST = frozenset({
    "openrouter/owl-alpha",
    "openrouter/free",
})


def openrouter_price_is_zero(price: str | float | None) -> bool:
    """True when OpenRouter pricing field is explicitly zero (free tier)."""
    if price is None:
        return False
    try:
        return float(price) == 0.0
    except (TypeError, ValueError):
        return False


def is_openrouter_free_model(
    model_id: str,
    prompt_price: str | float | None = None,
    completion_price: str | float | None = None,
) -> bool:
    """OpenRouter free models use :free suffix, zero pricing, or explicit allowlist."""
    mid = (model_id or "").strip().lower()
    if mid in OPENROUTER_FREE_ALLOWLIST:
        return True
    if mid.endswith(":free"):
        return True
    return openrouter_price_is_zero(prompt_price) and openrouter_price_is_zero(completion_price)


def normalize_model_id(provider: str, model: str) -> str:
    """Fix duplicated OpenRouter prefixes from dashboard display."""
    model = (model or "").strip()
    if provider == "openrouter":
        while model.startswith("openrouter/openrouter/"):
            model = model[len("openrouter/") :]
    return model


@dataclass
class LLMConfig:
    provider: str = "openai"  # openai, anthropic, ollama, together, groq, openrouter, api
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str | None = None
    max_tokens: int = 2048
    temperature: float = 0.7
    fallback_model: str | None = None
    # Some OpenAI-compatible reasoning models (e.g. LongCat-2.0) only return their
    # answer as streamed `content` deltas after `reasoning_content`; a non-stream
    # call yields empty content. Set stream: true for those providers.
    stream: bool = False

    # Provider presets: maps provider name -> (base_url, default_model)
    PROVIDER_PRESETS: dict = field(default_factory=lambda: {
        "openai":      (None, "gpt-4o"),
        "anthropic":   (None, "claude-sonnet-4-20250514"),
        "ollama":      ("http://localhost:11434/v1", "llama3"),
        "longcat":     ("https://api.longcat.chat/openai/v1", "LongCat-2.0"),
        "together":    ("https://api.together.xyz/v1", "meta-llama/Llama-3-70b-chat-hf"),
        "groq":        ("https://api.groq.com/openai/v1", "llama3-70b-8192"),
        "openrouter":  ("https://openrouter.ai/api/v1", DEFAULT_OPENROUTER_FREE_MODEL),
        "deepseek":    ("https://api.deepseek.com/v1", "deepseek-chat"),
        "fireworks":   ("https://api.fireworks.ai/inference/v1", "accounts/fireworks/models/llama-v3-70b-instruct"),
        "zenmux":      ("https://zenmux.ai/api/v1", "bytedance/doubao-seed-2.1-pro"),
        "api":         (None, "gpt-4o"),  # generic -- user provides base_url + api_key
    })

    def resolve(self) -> tuple[str | None, str]:
        """Return (base_url, api_key) after applying provider presets."""
        preset = self.PROVIDER_PRESETS.get(self.provider)
        url = self.base_url
        key = self.api_key

        if preset and not url:
            url = preset[0]

        # Ollama doesn't need a real key
        if self.provider == "ollama" and not key:
            key = "ollama"

        if not key and self.provider != "ollama":
            key = resolve_provider_api_key(self.provider)

        return url, key


# Shared provider preset table (base_url, default_model) — single source of truth,
# reused by the dashboard's "Other providers" panel so it doesn't hardcode a second copy.
PROVIDER_PRESETS: dict[str, tuple[str | None, str]] = LLMConfig().PROVIDER_PRESETS

# Env var each provider's key is read from. "openai" is intentionally absent —
# it keeps the legacy NEWAPI_API_KEY-first lookup in resolve_provider_api_key().
PROVIDER_API_KEY_ENV: dict[str, str] = {
    "openrouter": "OPENROUTER_API_KEY",
    "longcat": "LONGCAT_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "together": "TOGETHER_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "zenmux": "ZENMUX_API_KEY",
    "api": "API_KEY",
}

# Providers with no sensible default base_url — the user must supply one.
PROVIDER_NEEDS_BASE_URL = frozenset({"api"})

# Providers offered in the dashboard's "Other providers" panel (excludes ollama/openrouter,
# which already have dedicated tabs).
OTHER_PROVIDERS = ("openai", "anthropic", "together", "groq", "deepseek", "fireworks", "zenmux", "api")


def provider_key_env_name(provider: str) -> str:
    """Env var name a given provider's key lives under."""
    if provider == "openai":
        return "NEWAPI_API_KEY"
    return PROVIDER_API_KEY_ENV.get(provider, "")


def resolve_provider_api_key(provider: str) -> str:
    """Look up a provider's API key from the environment or configured env files."""
    _load_env_files()
    if provider == "ollama":
        return ""
    if provider == "openai":
        return os.environ.get("NEWAPI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    env_name = PROVIDER_API_KEY_ENV.get(provider)
    return os.environ.get(env_name, "") if env_name else ""


def provider_key_status() -> dict[str, bool]:
    """Which of the 'other' providers currently have a usable key configured."""
    return {p: bool(resolve_provider_api_key(p)) for p in OTHER_PROVIDERS}


def save_api_key(provider: str, api_key: str) -> str:
    """Write/update a provider's key in the user env file and apply it to this process.

    Keys never live in config.yaml — same policy as the existing OPENROUTER_API_KEY handling.
    """
    env_name = provider_key_env_name(provider)
    if not env_name:
        raise ValueError(f"No API key env var known for provider: {provider}")
    env_path = USER_ENV_PATH
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    prefix = f"{env_name}="
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = f"{prefix}{api_key}"
            break
    else:
        lines.append(f"{prefix}{api_key}")
    env_path.write_text("\n".join(lines) + "\n")
    os.environ[env_name] = api_key
    return env_name


logger = logging.getLogger("syx-overlord.config")

DEFAULT_OLLAMA_FALLBACK_MODEL = os.environ.get("SYX_OLLAMA_MODEL", "qwen2.5:14b")


def ensure_llm_config(config: LLMConfig) -> LLMConfig:
    """Keep bridge/dashboard up when cloud keys are missing — fall back to Ollama."""
    _, key = config.resolve()
    if config.provider == "openrouter" and not (key or "").strip():
        logger.warning(
            "OPENROUTER_API_KEY not set — falling back to Ollama (%s). "
            "Set OPENROUTER_API_KEY in .env or switch provider in bridge/config.yaml.",
            DEFAULT_OLLAMA_FALLBACK_MODEL,
        )
        return replace(
            config,
            provider="ollama",
            model=DEFAULT_OLLAMA_FALLBACK_MODEL,
            base_url=DEFAULT_OLLAMA_URL,
            api_key="",
            fallback_model=None,
        )
    return config


@dataclass
class GameConfig:
    mod_url: str = "http://localhost:47823"
    poll_interval_seconds: int = 5
    command_rate_limit: int = 3


@dataclass
class DashboardConfig:
    port: int = 3847
    ws_enabled: bool = True


@dataclass
class OverlordConfig:
    persona: str = DEFAULT_PERSONA
    game_mode: str = DEFAULT_GAME_MODE

    @property
    def personality(self) -> str:
        """Legacy alias — persona id only."""
        return self.persona


@dataclass
class MapConfig:
    """Dashboard shows full settlement grid; LLM gets mapRows only when llm_enabled."""
    llm_enabled: bool = False


@dataclass
class VisionConfig:
    enabled: bool = False
    every_n_ticks: int = 5
    max_width: int = 1024
    model: str | None = None  # vision-capable model; defaults to llm.fallback_model


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    game: GameConfig = field(default_factory=GameConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    overlord: OverlordConfig = field(default_factory=OverlordConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    map: MapConfig = field(default_factory=MapConfig)


def load_config(path: str | Path = "config.yaml") -> Config:
    """Load configuration from YAML file with env var substitution."""
    _load_env_files()
    config_path = Path(path)
    if path == "config.yaml" and CONFIG_PATH.exists():
        config_path = CONFIG_PATH
    elif not config_path.is_absolute() and not config_path.exists():
        config_path = CONFIG_PATH if CONFIG_PATH.exists() else Path(__file__).parent.parent / "config.example.yaml"

    data = load_config_file(config_path) if config_path.exists() else {}

    llm_data = data.get("llm", {})
    game_data = data.get("game", {})
    dash_data = data.get("dashboard", {})
    overlord_data = data.get("overlord", {})
    vision_data = data.get("vision", {})
    map_data = data.get("map", {})
    provider = llm_data.get("provider", "openai")
    model = normalize_model_id(provider, llm_data.get("model", "gpt-4o"))
    key = llm_data.get("api_key") or resolve_provider_api_key(provider)

    fallback = llm_data.get("fallback_model")
    if fallback is None and provider == "openrouter":
        fallback = DEFAULT_OPENROUTER_FALLBACK
    if fallback:
        fallback = normalize_model_id(provider, fallback)

    vision_model = vision_data.get("model")
    if vision_model:
        vision_model = normalize_model_id(provider, vision_model)
    elif fallback:
        vision_model = fallback

    persona_id, game_mode_id = resolve_overlord_settings(overlord_data)
    llm = ensure_llm_config(
        LLMConfig(
            provider=provider,
            model=model,
            api_key=key,
            base_url=llm_data.get("base_url"),
            max_tokens=llm_data.get("max_tokens", 2048),
            temperature=llm_data.get("temperature", 0.7),
            fallback_model=fallback,
            stream=bool(llm_data.get("stream", False)),
        )
    )
    return Config(
        llm=llm,
        game=GameConfig(
            mod_url=os.environ.get(
                "SYX_MOD_URL",
                game_data.get("mod_url", "http://localhost:47823"),
            ),
            poll_interval_seconds=game_data.get("poll_interval_seconds", 5),
            command_rate_limit=game_data.get("command_rate_limit", 3),
        ),
        dashboard=DashboardConfig(
            port=int(os.environ.get("SYX_BRIDGE_PORT", dash_data.get("port", 3847))),
            ws_enabled=dash_data.get("ws_enabled", True),
        ),
        overlord=OverlordConfig(
            persona=normalize_persona_id(persona_id),
            game_mode=normalize_game_mode_id(game_mode_id),
        ),
        vision=VisionConfig(
            enabled=bool(vision_data.get("enabled", False)),
            every_n_ticks=int(vision_data.get("every_n_ticks", 5)),
            max_width=int(vision_data.get("max_width", 1024)),
            model=vision_model,
        ),
        map=MapConfig(
            llm_enabled=bool(map_data.get("llm_enabled", False)),
        ),
    )


def openrouter_api_key() -> str:
    _load_env_files()
    return os.environ.get("OPENROUTER_API_KEY", "")


def ollama_request_timeout() -> float:
    return 180.0


def ollama_native_url(base_url: str | None = None) -> str:
    """Ollama REST root (no /v1) for /api/tags etc."""
    url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return url.rstrip("/")


def ollama_v1_url_from_config(cfg: "Config | None" = None) -> str | None:
    """Ollama OpenAI-compatible base URL — only when Ollama is the active provider."""
    if not cfg or cfg.llm.provider != "ollama":
        return None
    if cfg.llm.base_url:
        return cfg.llm.base_url.rstrip("/")
    return DEFAULT_OLLAMA_URL.rstrip("/")


def ollama_host_for_display(cfg: "Config | None" = None) -> str:
    """Configured Ollama host for settings display (no API call)."""
    if cfg and cfg.llm.provider == "ollama" and cfg.llm.base_url:
        return ollama_native_url(cfg.llm.base_url)
    return ollama_native_url(DEFAULT_OLLAMA_URL)


def load_config_file(path: Path | None = None) -> dict[str, Any]:
    config_path = path or CONFIG_PATH
    if not config_path.exists():
        config_path = Path(__file__).parent.parent / "config.example.yaml"
    if not config_path.exists():
        return {}
    raw = config_path.read_text()
    for key, value in os.environ.items():
        raw = raw.replace(f"${{{key}}}", value)
    return yaml.safe_load(raw) or {}


def save_llm_settings(
    *,
    provider: str,
    model: str,
    base_url: str | None = None,
    path: Path | None = None,
) -> None:
    config_path = path or CONFIG_PATH
    data = load_config_file(config_path) if config_path.exists() else {}
    llm = data.setdefault("llm", {})
    llm["provider"] = provider
    llm["model"] = normalize_model_id(provider, model)
    llm.pop("api_key", None)  # keys live in env files only, never in config.yaml
    preset_url = PROVIDER_PRESETS.get(provider, (None, None))[0]
    if base_url is not None:
        llm["base_url"] = base_url
    elif preset_url is not None:
        llm["base_url"] = preset_url
    else:
        llm.pop("base_url", None)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def save_personality_settings(*, personality: str, path: Path | None = None) -> None:
    """Save persona (voice) — not game mode."""
    save_persona_settings(persona=personality, path=path)


def save_persona_settings(*, persona: str, path: Path | None = None) -> None:
    config_path = path or CONFIG_PATH
    data = load_config_file(config_path) if config_path.exists() else {}
    overlord = data.setdefault("overlord", {})
    pid = normalize_persona_id(persona)
    overlord["persona"] = pid
    overlord["personality"] = pid  # legacy readers
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def save_game_mode_settings(*, game_mode: str, path: Path | None = None) -> None:
    config_path = path or CONFIG_PATH
    data = load_config_file(config_path) if config_path.exists() else {}
    overlord = data.setdefault("overlord", {})
    overlord["game_mode"] = normalize_game_mode_id(game_mode)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
