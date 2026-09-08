"""OpenRouter free-tier model detection."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from bridge.config import LLMConfig, ensure_llm_config, is_openrouter_free_model, openrouter_price_is_zero
from bridge.main import app


def test_openrouter_price_is_zero():
    assert openrouter_price_is_zero(0) is True
    assert openrouter_price_is_zero("0") is True
    assert openrouter_price_is_zero(0.0) is True
    assert openrouter_price_is_zero("0.0000001") is False
    assert openrouter_price_is_zero(None) is False


def test_is_openrouter_free_model_suffix():
    assert is_openrouter_free_model("cohere/north-mini-code:free") is True
    assert is_openrouter_free_model("meta-llama/llama-3.3-70b-instruct") is False


def test_is_openrouter_free_model_zero_pricing():
    assert is_openrouter_free_model("vendor/model", "0", "0") is True
    assert is_openrouter_free_model("vendor/model", "0", "0.00001") is False


def test_ensure_llm_config_openrouter_without_key_falls_back_to_ollama(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    cfg = LLMConfig(provider="openrouter", model="openrouter/owl-alpha", api_key="")
    with patch("bridge.config.openrouter_api_key", return_value=""):
        out = ensure_llm_config(cfg)
    assert out.provider == "ollama"
    assert out.model == "qwen2.5:14b"


def test_update_llm_config_rejects_paid_openrouter_model():
    with patch("bridge.main.openrouter_api_key", return_value="sk-test"):
        with patch("bridge.main.save_llm_settings") as save_mock:
            with TestClient(app) as client:
                resp = client.post(
                    "/api/config/llm",
                    json={
                        "provider": "openrouter",
                        "model": "meta-llama/llama-3.3-70b-instruct",
                    },
                )
    data = resp.json()
    assert data["success"] is False
    assert "free" in data["message"].lower()
    save_mock.assert_not_called()
