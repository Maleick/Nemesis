"""Regression tests for secret-safe auth-path logging behavior."""

import asyncio

import pytest

import agents.litellm_startup as litellm_startup
from agents.tasks import chatbot
from common.logger import sanitize_log_detail


class _DummyPromptManager:
    def __init__(self, *_args, **_kwargs):
        pass

    def get_prompt(self, *_args, **_kwargs):
        return None

    def save_prompt(self, *_args, **_kwargs):
        return True


class _DummyLogger:
    def __init__(self):
        self.errors = []

    def debug(self, *_args, **_kwargs):
        return None

    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def error(self, message, **kwargs):
        self.errors.append({"message": message, "kwargs": kwargs})


class _DummyResponse:
    status = 401

    async def text(self):
        return "access_token=super-secret-token-value jwt=aaaaaaaaaaaa.bbbbbbbbbbbb.cccccccccccc"

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


class _DummySession:
    def __init__(self, *_args, **_kwargs):
        pass

    def get(self, *_args, **_kwargs):
        return _DummyResponse()

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


def _build_chatbot_agent(monkeypatch: pytest.MonkeyPatch) -> chatbot.ChatbotAgent:
    monkeypatch.setattr(chatbot, "PromptManager", _DummyPromptManager)
    monkeypatch.setattr(chatbot, "get_postgres_connection_str", lambda: "postgresql://unused")
    return chatbot.ChatbotAgent()


def test_sanitize_log_detail_redacts_secret_patterns():
    detail = "password=super-secret authorization=Bearer abcdef token=my-token-value"

    sanitized = sanitize_log_detail(detail, max_length=500)

    assert "super-secret" not in sanitized
    assert "my-token-value" not in sanitized
    assert "Bearer abcdef" not in sanitized
    assert "[REDACTED]" in sanitized


def test_chatbot_preflight_redacts_secret_literal_from_error(monkeypatch: pytest.MonkeyPatch):
    agent = _build_chatbot_agent(monkeypatch)

    def _raise_connect_error(_conn):
        raise RuntimeError("password=top-secret-value authentication failed")

    monkeypatch.setattr(chatbot.psycopg, "connect", _raise_connect_error)

    ok, error = agent._validate_chatbot_db_credentials()

    assert ok is False
    assert (error or "").startswith("auth_failed:")
    assert "top-secret-value" not in (error or "")


def test_litellm_validation_log_response_is_redacted(monkeypatch: pytest.MonkeyPatch):
    dummy_logger = _DummyLogger()

    monkeypatch.setattr(litellm_startup, "logger", dummy_logger)
    monkeypatch.setattr(litellm_startup.aiohttp, "ClientSession", _DummySession)

    result = asyncio.run(litellm_startup.validate_token("dummy-token"))

    assert result is False
    rendered = str(dummy_logger.errors)
    assert "super-secret-token-value" not in rendered
    assert "aaaaaaaaaaaa.bbbbbbbbbbbb.cccccccccccc" not in rendered
    assert "[REDACTED]" in rendered
