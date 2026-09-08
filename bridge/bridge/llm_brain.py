"""LLM brain -- formats game state into prompts and parses decisions."""
from __future__ import annotations

import json
import logging
import re
import time

from .config import LLMConfig
from .personalities import get_persona, get_game_mode, DEFAULT_PERSONA, DEFAULT_GAME_MODE
from .playbook import load_playbook, load_mode_context
from .models import GameState, LLMDecision, Command, state_for_llm
from .map_constants import MAX_THRONE_DISTANCE

logger = logging.getLogger(__name__)

_TICK_RULES = """
IMPORTANT RULES:
1. You receive game state as JSON. Analyze it carefully before deciding.
2. You MUST respond with a valid JSON decision object (no markdown, no extra text).
3. Limit yourself to 1-3 commands per turn to avoid overwhelming the system.
4. Consider population needs, resource balance, military readiness, and diplomacy.
5. Be strategic -- don't just react to immediate problems.

Your response MUST be valid JSON with this structure:
{
  "reasoning": "Your strategic analysis (2-3 sentences)",
  "mood": "one of: confident, cautious, aggressive, worried, pleased, frustrated",
  "commands": [
    {
      "action": "build|clear_placement|finish_construction|set_speed",
      "target": "description of what to build/affect",
      "x": null,
      "y": null,
      "params": {}
    }
  ]
}

Available actions:
- build: Place a building. target=room type (stockpile, home, well, farm, woodcutter, ...), x/y=coordinates near throne. Area rooms accept params.width and params.height (default 4). Prefer small footprints (≤6) — big areas in forest never finish.
- clear_placement: Clear TmpArea/placer ghost locks after collision spam (no x/y needed). Use when builds fail with TmpArea errors.
- finish_construction: Instant-finish all open construction sites (no x/y). Bridge auto-uses this when sites stall; you rarely need it.
- set_speed: Set game speed. params.value=0-4 (0=pause, 1=1x, 2=5x, 3≈25x, 4=250x). Use 2 while construction is open.
- demolish: NOT implemented — do not use
- set_policy: Change a policy. target=policy name, params.value=new value
- recruit: Recruit units. target=unit type, params.count=number
- set_tax: Set tax rate. params.value=0-100
- set_ration: Set food rations. params.value=ration level
"""

USER_PROMPT_TEMPLATE = """Current game state:

{state_summary}

Full state data:
{state_json}

History of recent decisions (last 3):
{recent_history}

{user_orders}

{map_pins}

SESSION MEMORY (this game only):
{session_memory}

PERSISTENT KNOWLEDGE (all prior games — obey blacklists):
{persistent_knowledge}

{vision_note}

What is your next command? Respond with JSON only."""

_CHAT_RULES = """
Answer in plain text (2-5 sentences).

PERSONA vs GAME MODE (both apply — do not merge them):
- PERSONA = voice and character (how you speak, what you call the player).
- GAME MODE = tactical playbook (optimal next moves, phase priorities, room/failure rules).
Stay fully in persona voice while giving game-mode strategic guidance. Never drop persona
for a neutral assistant tone. Cite room rules and failure patterns when relevant to the advice.

- If they ask a question, answer using the game state and session memory provided.
- If they ask about your wiki or playbook: YES — you have a local rules wiki (playbook) injected into every decision tick, plus session memory (this game) and persistent knowledge (learned across games). You do NOT browse the web or external wikis; cite what you know from playbook + memory + knowledge + current state.
- If they give an order, acknowledge what you will prioritize on the next decision tick (in persona voice, per game mode priorities).
- If they ask what you are doing or why something failed, explain using recent history and memory.
- If they request an action that is not implemented (demolish, tax, policy, recruit, ration), say so and suggest build or set_speed instead.

Do NOT output JSON. Do NOT use markdown code fences."""


def _extract_openai_content(response) -> str:
    """Return non-empty text from an OpenAI-compatible chat completion."""
    if not getattr(response, "choices", None):
        raise ValueError("LLM returned no choices")
    message = response.choices[0].message
    if message is None:
        raise ValueError("LLM returned empty message")
    content = message.content
    if content is None or not str(content).strip():
        raise ValueError("LLM returned empty content")
    return str(content).strip()


def _extract_anthropic_content(response) -> str:
    """Return non-empty text from an Anthropic messages response."""
    if not getattr(response, "content", None):
        raise ValueError("LLM returned no content blocks")
    text = response.content[0].text
    if not text or not str(text).strip():
        raise ValueError("LLM returned empty content")
    return str(text).strip()


def _strip_markdown_fence(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return cleaned.strip()


def _extract_json_object(raw: str) -> str:
    """Best-effort extract a JSON object from noisy LLM output."""
    cleaned = _strip_markdown_fence(raw)
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def _repair_json(raw: str) -> str:
    """Remove trailing commas and control chars that break json.loads."""
    text = _extract_json_object(raw)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text


def _rate_limit_delay(exc: Exception) -> float:
    """Seconds to wait after 429 before retry/fallback (cap 30s)."""
    err = str(exc)
    if "429" not in err:
        return 0.0
    match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", err, re.IGNORECASE)
    if match:
        return min(float(match.group(1)) + 0.5, 30.0)
    match = re.search(r'"retryDelay":\s*"(\d+)s"', err)
    if match:
        return min(float(match.group(1)) + 0.5, 30.0)
    return 8.0


def _is_retriable_llm_error(exc: Exception) -> bool:
    err = str(exc).lower()
    for code in ("400", "401", "404", "429", "502", "503", "504"):
        if code in err:
            return True
    for phrase in (
        "connection error",
        "no choices",
        "empty content",
        "timeout",
        "invalid_model",
        "not valid",
    ):
        if phrase in err:
            return True
    return False


def _system_prompt(persona_id: str, game_mode_id: str) -> str:
    persona = get_persona(persona_id)
    mode = get_game_mode(game_mode_id)
    mode_block = load_mode_context(game_mode_id)
    return f"""You are an AI overlord controlling a fantasy city-state in Songs of Syx.
Your goal is to grow your civilization, keep your people alive, and defend against threats.

{persona.tick_voice}

{mode.tick_voice}

{_TICK_RULES}

""" + load_playbook() + mode_block


def _chat_system_prompt(persona_id: str, game_mode_id: str) -> str:
    persona = get_persona(persona_id)
    mode = get_game_mode(game_mode_id)
    mode_block = load_mode_context(game_mode_id)
    return f"""You are the ruler of a Songs of Syx settlement. The player is speaking to you directly.

{persona.chat_voice}

{mode.chat_voice}

{_CHAT_RULES}""" + (f"\n\n{mode_block}" if mode_block else "")


class LLMBrain:
    """Connects to an LLM and gets strategic decisions."""

    def __init__(
        self,
        config: LLMConfig,
        persona: str = DEFAULT_PERSONA,
        game_mode: str = DEFAULT_GAME_MODE,
        map_llm_enabled: bool = False,
    ):
        self.config = config
        self.persona = get_persona(persona).id
        self.game_mode = get_game_mode(game_mode).id
        self.map_llm_enabled = map_llm_enabled
        self._client = None
        self._init_client()

    def set_map_llm_enabled(self, enabled: bool) -> None:
        self.map_llm_enabled = bool(enabled)

    def set_persona(self, persona_id: str) -> None:
        self.persona = get_persona(persona_id).id

    def set_game_mode(self, game_mode_id: str) -> None:
        self.game_mode = get_game_mode(game_mode_id).id

    def set_personality(self, personality_id: str) -> None:
        """Legacy — sets persona only."""
        self.set_persona(personality_id)

    def _init_client(self):
        """Initialize the LLM client based on provider."""
        base_url, api_key = self.config.resolve()

        if self.config.provider == "anthropic":
            from anthropic import Anthropic
            self._client = Anthropic(api_key=api_key)
        else:
            from openai import OpenAI
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            timeout = 180.0 if self.config.provider == "ollama" else 90.0
            self._client = OpenAI(**kwargs, timeout=timeout)

    def decide(
        self,
        state: GameState,
        recent_history: list[str] | None = None,
        user_orders: list[str] | None = None,
        map_pins: str | None = None,
        session_memory: str | None = None,
        persistent_knowledge: str | None = None,
        screenshot_b64: str | None = None,
        vision_model: str | None = None,
    ) -> LLMDecision:
        """Get an LLM decision based on current game state."""
        orders_block = ""
        if user_orders:
            orders_block = "DIRECT ORDERS FROM THE PLAYER (follow these):\n" + "\n".join(
                f"- {o}" for o in user_orders
            )

        if screenshot_b64:
            vision_note = (
                "VISION: A settlement screenshot is attached to this request. "
                "Use it to see buildings, terrain, water, trees, and open tiles. "
                "Cross-check throne coords from JSON with what you see."
            )
        else:
            if not self.map_llm_enabled:
                vision_note = (
                    "MAP: Tile grid is OFF in this prompt (partial maps confuse placement). "
                    "Use throne coords, roomCounts, construction, memory, player pins, and "
                    f"spread builds up to {MAX_THRONE_DISTANCE} tiles from throne."
                )
            else:
                vision_note = (
                    "MAP: ASCII tile grid is in state summary (if exported by mod). "
                    "You cannot see pixels unless a screenshot is attached. "
                    "Use mapRows + throne coords + memory for placement."
                )

        include_map = self.map_llm_enabled
        user_prompt = USER_PROMPT_TEMPLATE.format(
            state_summary=state.summarize(include_map=include_map),
            state_json=json.dumps(state_for_llm(state, include_map=include_map), indent=2, default=str),
            recent_history="\n".join(recent_history[-3:]) if recent_history else "None yet",
            user_orders=orders_block,
            map_pins=map_pins or "",
            session_memory=session_memory or "No session memory yet.",
            persistent_knowledge=persistent_knowledge or "No persistent knowledge yet.",
            vision_note=vision_note,
        )

        try:
            if screenshot_b64:
                model = vision_model or self.config.fallback_model or self.config.model
                try:
                    return self._decide_openai_vision(user_prompt, screenshot_b64, model=model)
                except Exception as ve:
                    logger.warning(f"Vision tick failed ({ve}); falling back to text-only decision")
            if self.config.provider == "anthropic":
                return self._decide_anthropic(user_prompt)
            decision = self._decide_openai_with_fallback(user_prompt)
            if decision.mood == "confused" and not decision.commands:
                logger.info("Retrying LLM decision after empty/invalid JSON")
                time.sleep(1.0)
                decision = self._decide_openai_with_fallback(user_prompt)
            return decision
        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            return LLMDecision(
                reasoning=f"Error communicating with LLM: {e}",
                mood="frustrated",
                commands=[],
            )

    def reply_to_user(
        self,
        message: str,
        state: GameState | None,
        session_memory: str | None = None,
        persistent_knowledge: str | None = None,
        recent_history: list[str] | None = None,
        screenshot_b64: str | None = None,
        vision_model: str | None = None,
    ) -> str:
        """Plain-text reply when the player talks to the overlord."""
        if state:
            include_map = self.map_llm_enabled
            state_block = (
                f"Current summary:\n{state.summarize(include_map=include_map)}\n\n"
                f"Full state JSON:\n{json.dumps(state_for_llm(state, include_map=include_map), indent=2, default=str)}"
            )
        else:
            state_block = "Game state unavailable (mod API not connected). Answer from general knowledge and memory."

        vision_line = ""
        if screenshot_b64:
            vision_line = (
                "\nThe player attached a settlement screenshot — describe what you see "
                "(buildings, terrain, water, problems) and answer their message.\n"
            )

        user_prompt = f"""Player message:
{message.strip()}
{vision_line}
{state_block}

Recent decision history:
{chr(10).join(recent_history[-5:]) if recent_history else "None yet"}

Session memory (this game):
{session_memory or "No session memory yet."}

Persistent knowledge (learned across all games):
{persistent_knowledge or "No persistent knowledge yet."}

Local wiki / playbook (rules you follow each tick — summarize if asked):
{load_playbook()[:3500]}

Reply to the player now."""

        chat_system = _chat_system_prompt(self.persona, self.game_mode)
        try:
            if screenshot_b64:
                model = vision_model or self.config.fallback_model or self.config.model
                if self.config.provider == "anthropic":
                    response = self._client.messages.create(
                        model=self.config.model,
                        max_tokens=min(512, self.config.max_tokens),
                        system=chat_system,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": screenshot_b64,
                                    },
                                },
                            ],
                        }],
                    )
                    return _extract_anthropic_content(response)
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": chat_system},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{screenshot_b64}",
                                    },
                                },
                            ],
                        },
                    ],
                    max_tokens=min(512, self.config.max_tokens),
                    temperature=self.config.temperature,
                )
                return _extract_openai_content(response)
            if self.config.provider == "anthropic":
                response = self._client.messages.create(
                    model=self.config.model,
                    max_tokens=min(512, self.config.max_tokens),
                    system=chat_system,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return _extract_anthropic_content(response)
            # reasoning models (stream) need room for reasoning + the answer;
            # non-reasoning replies stay short.
            reply_tokens = self.config.max_tokens if self.config.stream else min(512, self.config.max_tokens)
            return self._openai_chat(
                [
                    {"role": "system", "content": chat_system},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.config.model,
                max_tokens=reply_tokens,
                temperature=self.config.temperature,
                want_json=False,
            )
        except Exception as e:
            logger.error(f"LLM chat reply failed: {e}")
            return f"I cannot reach my advisors right now ({e}). Try again in a moment."

    def _openai_chat(
        self,
        messages: list,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        want_json: bool = False,
    ) -> str:
        """One OpenAI-compatible chat call, returning text content.

        Streams when config.stream is set — required for reasoning models like
        LongCat-2.0, whose answer only arrives as `content` deltas after a run of
        `reasoning_content` deltas; a non-stream call to them returns empty content.
        """
        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        def _call(use_json: bool) -> str:
            k = dict(kwargs)
            # response_format json_object BREAKS streamed reasoning models (LongCat-2.0
            # then emits only reasoning_content and no answer). When streaming, omit it
            # and let the prompt + _parse_decision recover the JSON from the text.
            if use_json and not self.config.stream:
                k["response_format"] = {"type": "json_object"}
            if self.config.stream:
                parts: list[str] = []
                for chunk in self._client.chat.completions.create(**k, stream=True):
                    if not getattr(chunk, "choices", None):
                        continue
                    # take answer `content` only; skip the model's `reasoning_content`
                    piece = getattr(chunk.choices[0].delta, "content", None)
                    if piece:
                        parts.append(piece)
                text = "".join(parts).strip()
                if not text:
                    raise ValueError("LLM returned empty content")
                return text
            return _extract_openai_content(self._client.chat.completions.create(**k))

        try:
            return _call(want_json)
        except Exception as e:
            err = str(e).lower()
            if want_json and ("response_format" in err or "json_object" in err or "400" in err):
                return _call(False)
            raise

    def _decide_openai_with_fallback(self, user_prompt: str) -> LLMDecision:
        try:
            return self._decide_openai(user_prompt, model=self.config.model)
        except Exception as e:
            fb = self.config.fallback_model
            if (
                not fb
                or fb == self.config.model
                or self.config.provider
                not in ("openrouter", "openai", "api", "zenmux", "together", "groq", "deepseek", "fireworks")
                or not _is_retriable_llm_error(e)
            ):
                raise
            delay = _rate_limit_delay(e)
            if delay:
                logger.info(f"Rate limited — waiting {delay:.1f}s before fallback")
                time.sleep(delay)
            logger.warning(
                f"Primary model {self.config.model} failed ({e}); "
                f"retrying with fallback {fb}"
            )
            return self._decide_openai(user_prompt, model=fb)

    def _decide_openai(self, user_prompt: str, *, model: str | None = None) -> LLMDecision:
        model = model or self.config.model
        messages = [
            {"role": "system", "content": _system_prompt(self.persona, self.game_mode)},
            {"role": "user", "content": user_prompt},
        ]
        content = self._openai_chat(
            messages,
            model=model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            want_json=True,
        )
        return self._parse_decision(content)

    def _decide_openai_vision(
        self,
        user_prompt: str,
        screenshot_b64: str,
        *,
        model: str,
    ) -> LLMDecision:
        content_parts = [
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
            },
        ]
        messages = [
            {"role": "system", "content": _system_prompt(self.persona, self.game_mode)},
            {"role": "user", "content": content_parts},
        ]
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
        except Exception as e:
            fb = self.config.fallback_model
            if fb and fb != model and _is_retriable_llm_error(e):
                delay = _rate_limit_delay(e)
                if delay:
                    logger.info(f"Vision rate limited — waiting {delay:.1f}s before fallback")
                    time.sleep(delay)
                logger.warning(f"Vision model {model} failed ({e}); retry {fb}")
                response = self._client.chat.completions.create(
                    model=fb,
                    messages=messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
            else:
                raise
        content = _extract_openai_content(response)
        return self._parse_decision(content)

    def _decide_anthropic_vision(self, user_prompt: str, screenshot_b64: str) -> LLMDecision:
        response = self._client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=_system_prompt(self.persona, self.game_mode),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": screenshot_b64,
                        },
                    },
                ],
            }],
        )
        content = _extract_anthropic_content(response)
        return self._parse_decision(content)

    def _decide_anthropic(self, user_prompt: str) -> LLMDecision:
        response = self._client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=_system_prompt(self.persona, self.game_mode),
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = _extract_anthropic_content(response)
        return self._parse_decision(content)

    def _parse_decision(self, raw: str | None) -> LLMDecision:
        """Parse LLM response into a structured decision."""
        if raw is None or not str(raw).strip():
            return LLMDecision(
                reasoning="LLM returned an empty response — retry next tick",
                mood="confused",
                commands=[],
            )

        cleaned = _repair_json(str(raw))
        data = None
        last_err: Exception | None = None
        for attempt in (cleaned, _extract_json_object(str(raw))):
            try:
                data = json.loads(attempt)
                break
            except json.JSONDecodeError as e:
                last_err = e

        if data is None:
            logger.warning(f"Failed to parse LLM response as JSON: {last_err}")
            logger.debug(f"Raw response: {raw}")
            return LLMDecision(
                reasoning=f"Failed to parse decision: {str(raw)[:200]}",
                mood="confused",
                commands=[],
            )

        try:
            commands = [Command(**c) for c in data.get("commands", [])]
            return LLMDecision(
                reasoning=data.get("reasoning", "No reasoning provided"),
                mood=data.get("mood", "neutral"),
                commands=commands,
            )
        except Exception as e:
            logger.warning(f"Failed to build decision from JSON: {e}")
            return LLMDecision(
                reasoning=f"Failed to parse decision: {str(raw)[:200]}",
                mood="confused",
                commands=[],
            )

    def close(self):
        if hasattr(self._client, 'close'):
            self._client.close()
