"""Persona vs game mode separation."""
from bridge.llm_brain import _chat_system_prompt, _system_prompt
from bridge.personalities import resolve_overlord_settings
from bridge.playbook import load_mode_context


def test_resolve_overlord_settings_separate_axes():
    persona, mode = resolve_overlord_settings({
        "persona": "tyrant",
        "game_mode": "civil_flow",
    })
    assert persona == "tyrant"
    assert mode == "civil_flow"


def test_legacy_personality_game_mode_migrates():
    persona, mode = resolve_overlord_settings({"personality": "civil_flow"})
    assert persona == "gregg"
    assert mode == "civil_flow"


def test_chat_prompt_includes_persona_and_game_mode():
    prompt = _chat_system_prompt("tyrant", "civil_flow")
    assert "PERSONA — Tyrannical Anti-Christ" in prompt
    assert "GAME MODE — Civil Flow" in prompt
    assert "PERSONA vs GAME MODE" in prompt
    assert "Do NOT override persona" in prompt


def test_tick_prompt_includes_both_axes():
    prompt = _system_prompt("tyrant", "civil_flow")
    assert "PERSONA — Tyrannical Anti-Christ" in prompt
    assert "GAME MODE — Civil Flow" in prompt


def test_load_mode_context_uses_game_mode_id():
    block = load_mode_context("civil_flow")
    assert "CIVIL FLOW" in block or block == ""
