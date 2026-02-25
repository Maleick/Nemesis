"""Unit tests for chatbot DB credential preflight behavior."""

import asyncio
import sys
import types

import pytest

# Allow importing chatbot module in environments without libpq-backed psycopg.
_psycopg_stub = types.ModuleType("psycopg")
_psycopg_stub.connect = lambda *_args, **_kwargs: None
sys.modules.setdefault("psycopg", _psycopg_stub)

from agents.tasks import chatbot


class _DummyPromptManager:
    """Prompt manager stub to avoid DB coupling in unit tests."""

    def __init__(self, *_args, **_kwargs):
        pass

    def get_prompt(self, *_args, **_kwargs):
        return None

    def save_prompt(self, *_args, **_kwargs):
        return True


class _DummyCursor:
    def execute(self, _query: str):
        return None

    def fetchone(self):
        return (1,)

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False


class _DummyConnection:
    def cursor(self):
        return _DummyCursor()

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False


def _build_chatbot_agent(monkeypatch: pytest.MonkeyPatch) -> chatbot.ChatbotAgent:
    monkeypatch.setattr(chatbot, "PromptManager", _DummyPromptManager)
    monkeypatch.setattr(chatbot, "get_postgres_connection_str", lambda: "postgresql://unused")
    return chatbot.ChatbotAgent()


def test_validate_chatbot_db_credentials_success(monkeypatch: pytest.MonkeyPatch):
    agent = _build_chatbot_agent(monkeypatch)
    monkeypatch.setattr(chatbot.psycopg, "connect", lambda _conn: _DummyConnection())

    ok, error = agent._validate_chatbot_db_credentials()

    assert ok is True
    assert error is None


def test_validate_chatbot_db_credentials_failure(monkeypatch: pytest.MonkeyPatch):
    agent = _build_chatbot_agent(monkeypatch)

    def _raise_connect_error(_conn):
        raise RuntimeError("invalid password")

    monkeypatch.setattr(chatbot.psycopg, "connect", _raise_connect_error)

    ok, error = agent._validate_chatbot_db_credentials()

    assert ok is False
    assert "invalid password" in (error or "")


def test_start_mcp_server_fails_fast_on_preflight_error(monkeypatch: pytest.MonkeyPatch):
    agent = _build_chatbot_agent(monkeypatch)

    async def _unhealthy_mcp() -> bool:
        return False

    monkeypatch.setattr(agent, "_check_mcp_health", _unhealthy_mcp)
    monkeypatch.setattr(agent, "_validate_chatbot_db_credentials", lambda: (False, "invalid password"))

    with pytest.raises(RuntimeError, match="Chatbot DB credential preflight failed"):
        asyncio.run(agent.start_mcp_server())


def test_start_mcp_server_preflight_error_does_not_leak_password(monkeypatch: pytest.MonkeyPatch):
    agent = _build_chatbot_agent(monkeypatch)

    async def _unhealthy_mcp() -> bool:
        return False

    monkeypatch.setenv("CHATBOT_DB_PASSWORD", "top-secret-value")
    monkeypatch.setattr(agent, "_check_mcp_health", _unhealthy_mcp)
    monkeypatch.setattr(agent, "_validate_chatbot_db_credentials", lambda: (False, "password authentication failed"))

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(agent.start_mcp_server())

    message = str(exc_info.value)
    assert "CHATBOT_DB_PASSWORD" in message
    assert "top-secret-value" not in message
