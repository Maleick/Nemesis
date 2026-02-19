"""Unit tests for codex_oauth auth.json resolution paths."""

import json
from pathlib import Path

from agents.auth_modes import LLMAuthMode
from agents.auth_provider import _resolve_codex_oauth


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _set_codex_env(monkeypatch, profile_path: Path) -> None:
    monkeypatch.setenv("LLM_AUTH_MODE", "codex_oauth")
    monkeypatch.setenv("CODEX_AUTH_EXPERIMENTAL", "true")
    monkeypatch.setenv("CODEX_AUTH_PROFILE_PATH", str(profile_path))
    monkeypatch.setenv("CODEX_AUTH_PROFILE_NAME", "openai-codex:default")
    monkeypatch.setenv("CODEX_BASE_URL", "https://chatgpt.com/backend-api/codex")
    monkeypatch.setenv("CODEX_MODEL", "gpt-5.3-codex-spark")


def test_codex_oauth_auth_json_happy_path(tmp_path, monkeypatch):
    auth_path = tmp_path / "auth.json"
    _write_json(
        auth_path,
        {
            "auth_mode": "chatgpt",
            "tokens": {
                "access_token": "header.payload.signature",
                "refresh_token": "refresh",
            },
        },
    )
    _set_codex_env(monkeypatch, auth_path)

    result = _resolve_codex_oauth(mode_fallback=False)

    assert result.mode is LLMAuthMode.CODEX_OAUTH
    assert result.healthy is True
    assert result.source == "codex_auth_json"
    assert result.token == "header.payload.signature"
    assert result.profile_path == str(auth_path)


def test_codex_oauth_auth_json_missing_access_token(tmp_path, monkeypatch):
    auth_path = tmp_path / "auth.json"
    _write_json(
        auth_path,
        {
            "auth_mode": "chatgpt",
            "tokens": {
                "refresh_token": "refresh-only",
            },
        },
    )
    _set_codex_env(monkeypatch, auth_path)

    result = _resolve_codex_oauth(mode_fallback=False)

    assert result.mode is LLMAuthMode.CODEX_OAUTH
    assert result.healthy is False
    assert result.token is None
    assert "does not include a usable tokens.access_token" in result.message


def test_codex_oauth_auth_json_invalid_json(tmp_path, monkeypatch):
    auth_path = tmp_path / "auth.json"
    auth_path.write_text("{not-valid-json", encoding="utf-8")
    _set_codex_env(monkeypatch, auth_path)

    result = _resolve_codex_oauth(mode_fallback=False)

    assert result.mode is LLMAuthMode.CODEX_OAUTH
    assert result.healthy is False
    assert result.token is None
    assert result.message == "Unable to load Codex auth profile JSON."
