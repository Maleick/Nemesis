"""Tests for /system/llm-auth-status proxy and fallback behavior."""

import requests


def test_llm_auth_status_returns_agents_payload(client, monkeypatch):
    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "mode": "codex_oauth",
                "healthy": True,
                "available": True,
                "source": "agents",
                "message": "ok",
                "model_name": "gpt-5.3-codex-spark",
                "base_url": "https://chatgpt.com/backend-api/codex",
            }

    monkeypatch.setattr("web_api.main.requests.get", lambda *args, **kwargs: DummyResponse())

    response = client.get("/system/llm-auth-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "codex_oauth"
    assert payload["healthy"] is True
    assert payload["source"] == "agents"


def test_llm_auth_status_invalid_mode_forces_unhealthy_payload(client, monkeypatch):
    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "mode": "codex_oauth",
                "healthy": True,
                "available": True,
                "source": "agents",
                "message": "ok",
                "model_name": "gpt-5.3-codex-spark",
                "base_url": "https://chatgpt.com/backend-api/codex",
            }

    monkeypatch.setenv("LLM_AUTH_MODE", "invalid-mode")
    monkeypatch.setattr("web_api.main.requests.get", lambda *args, **kwargs: DummyResponse())

    response = client.get("/system/llm-auth-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "official_key"
    assert payload["healthy"] is False
    assert payload["available"] is False
    assert "Unsupported LLM_AUTH_MODE" in payload["message"]


def test_llm_auth_status_non_200_returns_fallback(client, monkeypatch):
    class DummyResponse:
        status_code = 503

        @staticmethod
        def json():
            return {"error": "unavailable"}

    monkeypatch.setattr("web_api.main.requests.get", lambda *args, **kwargs: DummyResponse())

    response = client.get("/system/llm-auth-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["healthy"] is False
    assert payload["available"] is False
    assert payload["source"] == "web-api-fallback"
    assert "returned 503" in payload["message"]


def test_llm_auth_status_request_exception_returns_fallback(client, monkeypatch):
    def _raise(*args, **kwargs):
        raise requests.RequestException("connection failed")

    monkeypatch.setattr("web_api.main.requests.get", _raise)

    response = client.get("/system/llm-auth-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["healthy"] is False
    assert payload["available"] is False
    assert payload["source"] == "web-api-fallback"
    assert payload["message"] == "Failed retrieving LLM auth status from agents service"


class _DummyCursor:
    def execute(self, _query):
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


class _DummyPool:
    def connection(self):
        return _DummyConnection()


async def _healthy_llm_auth():
    return {"healthy": True, "mode": "official_key", "source": "agents", "message": "ok"}


async def _unhealthy_llm_auth():
    return {"healthy": False, "mode": "codex_oauth", "source": "agents", "message": "Auth unavailable"}


def test_system_health_reports_degraded_when_llm_auth_unavailable(client, monkeypatch):
    monkeypatch.setattr("web_api.main.get_db_pool", lambda: _DummyPool())
    monkeypatch.setattr("web_api.main.get_llm_auth_status", _unhealthy_llm_auth)

    response = client.get("/system/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["readiness"] == "degraded"
    dependency = {d["name"]: d for d in payload["dependencies"]}
    assert dependency["agents-llm-auth"]["readiness"] == "degraded"


def test_system_health_reports_unhealthy_when_postgres_is_down(client, monkeypatch):
    def _raise_pool():
        raise RuntimeError("connection refused")

    monkeypatch.setattr("web_api.main.get_db_pool", _raise_pool)
    monkeypatch.setattr("web_api.main.get_llm_auth_status", _healthy_llm_auth)

    response = client.get("/system/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unhealthy"
    assert payload["readiness"] == "unhealthy"
    dependency = {d["name"]: d for d in payload["dependencies"]}
    assert dependency["postgres"]["readiness"] == "unhealthy"
