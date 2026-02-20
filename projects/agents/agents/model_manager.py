"""Centralized model management for all agent activities."""

from datetime import UTC, datetime

import structlog
from agents.codex_oauth_model import CodexOAuthResponsesModel
from agents.helpers import create_rate_limit_client
from agents.logger import setup_phoenix_llm_tracing
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

logger = structlog.get_logger(__name__)


class ModelManager:
    """Singleton manager for LLM model instances used across all activities."""

    _model: Model | None = None
    _token: str | None = None
    _model_name: str | None = None
    _base_url: str = "http://litellm:4000/"
    _auth_mode: str = "official_key"
    _auth_source: str = "litellm"
    _auth_message: str = "Model manager not initialized"
    _token_expires_at: datetime | None = None
    _last_updated: datetime | None = None
    _instrumentation_enabled: bool = False

    @classmethod
    def initialize(
        cls,
        token: str,
        model_name: str = "default",
        base_url: str = "http://litellm:4000/",
        auth_mode: str = "official_key",
        auth_source: str = "litellm",
        auth_message: str = "LLM authentication is healthy",
        token_expires_at: datetime | None = None,
    ) -> None:
        """
        Initialize the model manager with runtime model credentials.
        Called once during application startup in lifespan().

        Args:
            token: Runtime API token
            model_name: Name of the model to use
            base_url: OpenAI-compatible base URL
            auth_mode: Runtime auth mode
            auth_source: Runtime auth source
            auth_message: Safe status message for operators
            token_expires_at: Optional token expiry timestamp
        """
        cls._token = token
        cls._model_name = model_name
        cls._base_url = base_url
        cls._auth_mode = auth_mode
        cls._auth_source = auth_source
        cls._auth_message = auth_message
        cls._token_expires_at = token_expires_at
        cls._last_updated = datetime.now(UTC)
        cls._model = None  # Reset model to force recreation with new config

        # Setup Phoenix tracing for LLM calls if enabled
        cls._instrumentation_enabled = setup_phoenix_llm_tracing()

        logger.info(
            "ModelManager initialized",
            model_name=model_name,
            auth_mode=auth_mode,
            auth_source=auth_source,
            base_url=base_url,
            phoenix_enabled=cls._instrumentation_enabled,
        )

    @classmethod
    def mark_unavailable(
        cls,
        auth_mode: str,
        message: str,
        model_name: str | None = None,
        base_url: str = "http://litellm:4000/",
        auth_source: str = "unknown",
        token_expires_at: datetime | None = None,
    ) -> None:
        """Record unavailable auth/model state without exposing token material."""
        cls._token = None
        cls._model = None
        cls._model_name = model_name
        cls._base_url = base_url
        cls._auth_mode = auth_mode
        cls._auth_source = auth_source
        cls._auth_message = message
        cls._token_expires_at = token_expires_at
        cls._last_updated = datetime.now(UTC)
        cls._instrumentation_enabled = False

        logger.warning(
            "ModelManager marked unavailable",
            auth_mode=auth_mode,
            auth_source=auth_source,
            model_name=model_name,
            reason=message,
        )

    @classmethod
    def get_model(cls) -> Model | None:
        """
        Get the shared model instance, creating it if necessary.

        Returns:
            Model instance or None if not initialized
        """
        if not cls.is_available():
            logger.warning("ModelManager not initialized - no valid token available")
            return None

        if not cls._model:
            try:
                provider = OpenAIProvider(base_url=cls._base_url, api_key=cls._token, http_client=create_rate_limit_client())

                if cls._auth_mode == "codex_oauth":
                    cls._model = CodexOAuthResponsesModel(
                        model_name=cls._model_name,  # pyright: ignore[reportArgumentType]
                        provider=provider,
                    )
                else:
                    cls._model = OpenAIModel(
                        model_name=cls._model_name,  # pyright: ignore[reportArgumentType]
                        provider=provider,
                    )

                logger.info("Created model instance", model_name=cls._model_name, auth_mode=cls._auth_mode)
            except Exception as e:
                logger.error(f"Failed to create model: {e}")
                return None

        return cls._model

    @classmethod
    def is_available(cls) -> bool:
        """Check if a model is available for use."""
        if cls._token is None:
            return False
        if cls._token_expires_at and cls._token_expires_at <= datetime.now(UTC):
            return False
        return True

    @classmethod
    def is_instrumentation_enabled(cls) -> bool:
        """Check if Phoenix LLM instrumentation is enabled."""
        return cls._instrumentation_enabled

    @classmethod
    def get_auth_status(cls) -> dict:
        """Return secret-safe status metadata for operators and UI surfaces."""
        now = datetime.now(UTC)
        expires_in_seconds: int | None = None
        token_expired = False
        if cls._token_expires_at:
            expires_in_seconds = int((cls._token_expires_at - now).total_seconds())
            token_expired = cls._token_expires_at <= now

        available = cls._token is not None and not token_expired
        message = cls._auth_message
        if token_expired:
            message = f"{message} Token has expired."

        return {
            "mode": cls._auth_mode,
            "healthy": available,
            "available": available,
            "source": cls._auth_source,
            "message": message,
            "model_name": cls._model_name,
            "base_url": cls._base_url,
            "expires_at": cls._token_expires_at.isoformat() if cls._token_expires_at else None,
            "expires_in_seconds": expires_in_seconds,
            "last_updated": cls._last_updated.isoformat() if cls._last_updated else None,
            "instrumentation_enabled": cls._instrumentation_enabled,
        }
