"""Unit tests for codex_oauth access-token expiry handling."""

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agents.auth_provider import _resolve_codex_oauth


def _jwt_with_exp(exp: datetime) -> str:
    header = {"alg": "none", "typ": "JWT"}
    payload = {"exp": int(exp.timestamp())}

    def _part(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    return f"{_part(header)}.{_part(payload)}."


def _write_auth_json(path: Path, token: str) -> None:
    payload = {
        "auth_mode": "chatgpt",
        "tokens": {
            "access_token": token,
            "refresh_token": "refresh",
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _set_env(monkeypatch, auth_path: Path) -> None:
    monkeypatch.setenv("LLM_AUTH_MODE", "codex_oauth")
    monkeypatch.setenv("CODEX_AUTH_EXPERIMENTAL", "true")
    monkeypatch.setenv("CODEX_AUTH_PROFILE_PATH", str(auth_path))
    monkeypatch.setenv("CODEX_AUTH_PROFILE_NAME", "openai-codex:default")
    monkeypatch.setenv("CODEX_MODEL", "gpt-5.3-codex-spark")
    monkeypatch.setenv("CODEX_BASE_URL", "https://chatgpt.com/backend-api/codex")


def test_access_token_expired_reports_unhealthy(tmp_path, monkeypatch):
    auth_path = tmp_path / "auth.json"
    expired = datetime.now(UTC) - timedelta(minutes=5)
    _write_auth_json(auth_path, _jwt_with_exp(expired))
    _set_env(monkeypatch, auth_path)

    result = _resolve_codex_oauth(mode_fallback=False)

    assert result.healthy is False
    assert result.token is None
    assert result.expires_at is not None
    assert "expired or about to expire" in result.message


def test_access_token_within_grace_window_reports_unhealthy(tmp_path, monkeypatch):
    auth_path = tmp_path / "auth.json"
    near_expiry = datetime.now(UTC) + timedelta(seconds=20)
    _write_auth_json(auth_path, _jwt_with_exp(near_expiry))
    _set_env(monkeypatch, auth_path)

    result = _resolve_codex_oauth(mode_fallback=False)

    assert result.healthy is False
    assert result.token is None
    assert result.expires_at is not None
    assert "expired or about to expire" in result.message


def test_access_token_after_grace_window_reports_healthy(tmp_path, monkeypatch):
    auth_path = tmp_path / "auth.json"
    valid = datetime.now(UTC) + timedelta(hours=2)
    _write_auth_json(auth_path, _jwt_with_exp(valid))
    _set_env(monkeypatch, auth_path)

    result = _resolve_codex_oauth(mode_fallback=False)

    assert result.healthy is True
    assert result.token is not None
    assert result.expires_at is not None
