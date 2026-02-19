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
