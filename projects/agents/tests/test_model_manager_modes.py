"""Unit tests for ModelManager auth-mode behavior."""

from datetime import UTC, datetime, timedelta

from agents import model_manager
from agents.model_manager import ModelManager


def _reset_model_manager():
    ModelManager._model = None
    ModelManager._token = None
    ModelManager._model_name = None
    ModelManager._base_url = "http://litellm:4000/"
    ModelManager._auth_mode = "official_key"
    ModelManager._auth_source = "litellm"
    ModelManager._auth_message = "Model manager not initialized"
    ModelManager._token_expires_at = None
    ModelManager._last_updated = None
    ModelManager._instrumentation_enabled = False


def test_mark_unavailable_sets_unhealthy_status():
    _reset_model_manager()

    ModelManager.mark_unavailable(
        auth_mode="codex_oauth",
        auth_source="codex_auth_json",
        message="token expired",
        model_name="gpt-5.3-codex-spark",
        base_url="https://chatgpt.com/backend-api/codex",
        token_expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    status = ModelManager.get_auth_status()
    assert status["mode"] == "codex_oauth"
    assert status["healthy"] is False
    assert status["available"] is False
    assert "expired" in status["message"]


def test_get_model_uses_openai_model_for_official_key(monkeypatch):
    _reset_model_manager()

    created = {"provider": None, "model_name": None}

    class DummyProvider:
        def __init__(self, **kwargs):
            created["provider"] = kwargs

    class DummyOpenAIModel:
        def __init__(self, model_name, provider):
            created["model_name"] = model_name
            self.model_name = model_name
            self.provider = provider

    monkeypatch.setattr(model_manager, "setup_phoenix_llm_tracing", lambda: False)
    monkeypatch.setattr(model_manager, "OpenAIProvider", DummyProvider)
    monkeypatch.setattr(model_manager, "OpenAIModel", DummyOpenAIModel)

    ModelManager.initialize(
        token="test-token",
        model_name="default",
        base_url="http://litellm:4000/",
        auth_mode="official_key",
        auth_source="litellm",
    )
    model = ModelManager.get_model()

    assert isinstance(model, DummyOpenAIModel)
    assert created["model_name"] == "default"
    assert created["provider"]["base_url"] == "http://litellm:4000/"
    assert created["provider"]["api_key"] == "test-token"


def test_get_model_uses_codex_model_for_codex_oauth(monkeypatch):
    _reset_model_manager()

    created = {"model_name": None}

    class DummyProvider:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class DummyCodexModel:
        def __init__(self, model_name, provider):
            created["model_name"] = model_name
            self.model_name = model_name
            self.provider = provider

    monkeypatch.setattr(model_manager, "setup_phoenix_llm_tracing", lambda: False)
    monkeypatch.setattr(model_manager, "OpenAIProvider", DummyProvider)
    monkeypatch.setattr(model_manager, "CodexOAuthResponsesModel", DummyCodexModel)

    ModelManager.initialize(
        token="oauth-token",
        model_name="gpt-5.3-codex-spark",
        base_url="https://chatgpt.com/backend-api/codex",
        auth_mode="codex_oauth",
        auth_source="codex_auth_json",
    )
    model = ModelManager.get_model()

    assert isinstance(model, DummyCodexModel)
    assert created["model_name"] == "gpt-5.3-codex-spark"
