"""Contract tests for auth-mode misconfiguration behavior."""

import asyncio

from agents.auth_modes import LLMAuthMode
import agents.auth_provider as auth_provider


def test_resolve_llm_auth_invalid_mode_reports_unhealthy(monkeypatch):
    monkeypatch.setenv("LLM_AUTH_MODE", "unsupported_mode")

    called = {"token_lookup": False}

    async def _token_lookup():
        called["token_lookup"] = True
        return "token"

    monkeypatch.setattr(auth_provider, "get_litellm_token", _token_lookup)

    result = asyncio.run(auth_provider.resolve_llm_auth())

    assert result.mode is LLMAuthMode.OFFICIAL_KEY
    assert result.healthy is False
    assert result.token is None
    assert result.source == "llm_auth_mode"
    assert "Unsupported LLM_AUTH_MODE" in result.message
    assert called["token_lookup"] is False


def test_resolve_llm_auth_empty_mode_reports_unhealthy(monkeypatch):
    monkeypatch.setenv("LLM_AUTH_MODE", "   ")

    result = asyncio.run(auth_provider.resolve_llm_auth())

    assert result.mode is LLMAuthMode.OFFICIAL_KEY
    assert result.healthy is False
    assert result.token is None
    assert result.source == "llm_auth_mode"
    assert "Unsupported LLM_AUTH_MODE" in result.message


def test_resolve_llm_auth_missing_mode_keeps_default_official_flow(monkeypatch):
    monkeypatch.delenv("LLM_AUTH_MODE", raising=False)

    async def _token_lookup():
        return None

    monkeypatch.setattr(auth_provider, "get_litellm_token", _token_lookup)

    result = asyncio.run(auth_provider.resolve_llm_auth())

    assert result.mode is LLMAuthMode.OFFICIAL_KEY
    assert result.healthy is False
    assert result.source == "litellm"
    assert "LiteLLM token is unavailable" in result.message
