"""Unit tests for CodexOAuthResponsesModel request default injection."""

import pytest
from agents.codex_oauth_model import (
    CodexOAuthResponsesModel,
    DEFAULT_CODEX_CLIENT_VERSION,
    DEFAULT_CODEX_INSTRUCTIONS,
)
from pydantic_ai.models.openai import OpenAIResponsesModel


@pytest.mark.asyncio
async def test_responses_create_injects_required_defaults(monkeypatch):
    captured = {}

    async def fake_super(self, messages, stream, model_settings, model_request_parameters):
        captured["messages"] = messages
        captured["stream"] = stream
        captured["model_settings"] = model_settings
        captured["model_request_parameters"] = model_request_parameters
        return "ok"

    monkeypatch.delenv("CODEX_CLIENT_VERSION", raising=False)
    monkeypatch.delenv("CODEX_DEFAULT_INSTRUCTIONS", raising=False)
    monkeypatch.setattr(OpenAIResponsesModel, "_responses_create", fake_super)

    model = object.__new__(CodexOAuthResponsesModel)
    result = await model._responses_create([], True, {}, None)

    assert result == "ok"
    assert captured["stream"] is True
    assert captured["model_settings"]["extra_headers"]["version"] == DEFAULT_CODEX_CLIENT_VERSION
    assert captured["model_settings"]["extra_body"]["store"] is False
    assert captured["model_settings"]["extra_body"]["instructions"] == DEFAULT_CODEX_INSTRUCTIONS


@pytest.mark.asyncio
async def test_responses_create_respects_explicit_overrides(monkeypatch):
    captured = {}

    async def fake_super(self, messages, stream, model_settings, model_request_parameters):
        captured["model_settings"] = model_settings
        return "ok"

    monkeypatch.setenv("CODEX_CLIENT_VERSION", "9.9.9")
    monkeypatch.setattr(OpenAIResponsesModel, "_responses_create", fake_super)

    model = object.__new__(CodexOAuthResponsesModel)
    settings = {
        "extra_headers": {"version": "1.2.3", "x-custom": "y"},
        "extra_body": {"store": True, "instructions": "custom"},
    }
    await model._responses_create([], True, settings, None)

    assert captured["model_settings"]["extra_headers"]["version"] == "1.2.3"
    assert captured["model_settings"]["extra_headers"]["x-custom"] == "y"
    assert captured["model_settings"]["extra_body"]["store"] is True
    assert captured["model_settings"]["extra_body"]["instructions"] == "custom"
