"""Resolve runtime LLM authentication mode and secret-safe status metadata."""

import base64
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from agents.auth_modes import LLMAuthMode
from agents.helpers import get_litellm_token

logger = structlog.get_logger(__name__)

TOKEN_EXPIRY_GRACE_PERIOD = timedelta(minutes=1)
DEFAULT_CODEX_PROFILE_NAME = "openai-codex:default"
DEFAULT_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
DEFAULT_CODEX_MODEL = "gpt-5.3-codex-spark"


def _is_truthy(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Codex auth profile JSON is invalid", path=str(path), error=str(exc))
        return None
    except OSError as exc:
        logger.warning("Unable to read Codex auth profile file", path=str(path), error=str(exc))
        return None

    if not isinstance(data, dict):
        logger.warning("Codex auth profile root is not an object", path=str(path))
        return None
    return data


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            numeric = float(value)
            # Some profile formats emit unix epoch in milliseconds.
            if numeric > 10_000_000_000:
                numeric = numeric / 1000.0
            return datetime.fromtimestamp(numeric, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None

        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    return None


def _extract_jwt_exp(raw_jwt: str | None) -> datetime | None:
    """Extract the exp claim from a JWT without validating the signature."""
    if not raw_jwt or "." not in raw_jwt:
        return None

    parts = raw_jwt.split(".")
    if len(parts) < 2:
        return None

    payload = parts[1]
    payload += "=" * (-len(payload) % 4)

    try:
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
        claims = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None

    if not isinstance(claims, dict):
        return None

    return _parse_datetime(claims.get("exp"))


def _extract_profile(document: dict[str, Any], profile_name: str) -> dict[str, Any] | None:
    profile_roots = []

    direct_profiles = document.get("profiles")
    if isinstance(direct_profiles, dict):
        profile_roots.append(direct_profiles)

    auth_root = document.get("auth")
    if isinstance(auth_root, dict):
        auth_profiles = auth_root.get("profiles")
        if isinstance(auth_profiles, dict):
            profile_roots.append(auth_profiles)

    for profiles in profile_roots:
        profile = profiles.get(profile_name)
        if isinstance(profile, dict):
            return profile

    return None


@dataclass(slots=True)
class LLMAuthResolution:
    mode: LLMAuthMode
    token: str | None
    model_name: str
    base_url: str
    healthy: bool
    message: str
    source: str
    expires_at: datetime | None = None
    profile_name: str | None = None
    profile_path: str | None = None

    def to_status_payload(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        expires_in_seconds: int | None = None
        if self.expires_at:
            expires_in_seconds = int((self.expires_at - now).total_seconds())

        return {
            "mode": self.mode.value,
            "healthy": self.healthy,
            "available": self.healthy and bool(self.token),
            "source": self.source,
            "message": self.message,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "profile_name": self.profile_name,
            "profile_path": self.profile_path,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "expires_in_seconds": expires_in_seconds,
        }


async def resolve_llm_auth() -> LLMAuthResolution:
    raw_mode = os.getenv("LLM_AUTH_MODE")
    mode, mode_fallback = LLMAuthMode.parse(raw_mode)

    # If the env var is present but invalid/empty, surface deterministic unhealthy status
    # instead of silently proceeding with fallback auth behavior.
    if mode_fallback or (raw_mode is not None and not raw_mode.strip()):
        configured_mode = raw_mode.strip() if raw_mode and raw_mode.strip() else "<empty>"
        return LLMAuthResolution(
            mode=LLMAuthMode.OFFICIAL_KEY,
            token=None,
            model_name=os.getenv("LITELLM_MODEL_NAME", "default"),
            base_url=os.getenv("LITELLM_OPENAI_BASE_URL", "http://litellm:4000/"),
            healthy=False,
            message=(
                f"Unsupported LLM_AUTH_MODE '{configured_mode}'. "
                "Set LLM_AUTH_MODE to 'official_key' or 'codex_oauth'."
            ),
            source="llm_auth_mode",
        )

    if mode == LLMAuthMode.OFFICIAL_KEY:
        return await _resolve_official_key(mode_fallback)
    return _resolve_codex_oauth(mode_fallback)


async def _resolve_official_key(mode_fallback: bool) -> LLMAuthResolution:
    token = await get_litellm_token()
    base_url = os.getenv("LITELLM_OPENAI_BASE_URL", "http://litellm:4000/")
    model_name = os.getenv("LITELLM_MODEL_NAME", "default")

    if mode_fallback:
        message = "Unknown LLM_AUTH_MODE value. Falling back to official_key."
    else:
        message = "Using LiteLLM admin-key provisioning flow."

    if not token:
        return LLMAuthResolution(
            mode=LLMAuthMode.OFFICIAL_KEY,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message=f"{message} LiteLLM token is unavailable.",
            source="litellm",
        )

    return LLMAuthResolution(
        mode=LLMAuthMode.OFFICIAL_KEY,
        token=token,
        model_name=model_name,
        base_url=base_url,
        healthy=True,
        message=message,
        source="litellm",
    )


def _resolve_codex_oauth(mode_fallback: bool) -> LLMAuthResolution:
    profile_name = os.getenv("CODEX_AUTH_PROFILE_NAME", DEFAULT_CODEX_PROFILE_NAME) or DEFAULT_CODEX_PROFILE_NAME
    profile_path = os.getenv("CODEX_AUTH_PROFILE_PATH")
    base_url = os.getenv("CODEX_BASE_URL", DEFAULT_CODEX_BASE_URL)
    model_name = os.getenv("CODEX_MODEL", DEFAULT_CODEX_MODEL)
    experimental_enabled = _is_truthy(os.getenv("CODEX_AUTH_EXPERIMENTAL"))

    if not experimental_enabled:
        return LLMAuthResolution(
            mode=LLMAuthMode.CODEX_OAUTH,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message=(
                "codex_oauth mode is gated. Set CODEX_AUTH_EXPERIMENTAL=true to enable this experimental auth path."
            ),
            source="codex_oauth_profile",
            profile_name=profile_name,
            profile_path=profile_path,
        )

    if not profile_path:
        return LLMAuthResolution(
            mode=LLMAuthMode.CODEX_OAUTH,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message="CODEX_AUTH_PROFILE_PATH is required for codex_oauth mode.",
            source="codex_oauth_profile",
            profile_name=profile_name,
            profile_path=profile_path,
        )

    path = Path(profile_path)
    document = _safe_load_json(path)
    if document is None:
        return LLMAuthResolution(
            mode=LLMAuthMode.CODEX_OAUTH,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message="Unable to load Codex auth profile JSON.",
            source="codex_oauth_profile",
            profile_name=profile_name,
            profile_path=profile_path,
        )

    # Codex CLI auth.json format
    #   {
    #     "auth_mode": "chatgpt",
    #     "tokens": {"access_token": "...", "refresh_token": "...", ...},
    #     ...
    #   }
    tokens = document.get("tokens")
    if isinstance(tokens, dict):
        access_token = tokens.get("access_token")
        if isinstance(access_token, str) and access_token.strip():
            expires_at = _extract_jwt_exp(access_token)
            if expires_at and expires_at <= datetime.now(UTC) + TOKEN_EXPIRY_GRACE_PERIOD:
                return LLMAuthResolution(
                    mode=LLMAuthMode.CODEX_OAUTH,
                    token=None,
                    model_name=model_name,
                    base_url=base_url,
                    healthy=False,
                    message="Codex auth.json access token is expired or about to expire.",
                    source="codex_auth_json",
                    expires_at=expires_at,
                    profile_name=profile_name,
                    profile_path=profile_path,
                )

            message = "Using experimental codex_oauth token from Codex CLI auth.json."
            if mode_fallback:
                message = f"{message} Unknown LLM_AUTH_MODE value was provided; codex_oauth selected by parser."

            return LLMAuthResolution(
                mode=LLMAuthMode.CODEX_OAUTH,
                token=access_token,
                model_name=model_name,
                base_url=base_url,
                healthy=True,
                message=message,
                source="codex_auth_json",
                expires_at=expires_at,
                profile_name=profile_name,
                profile_path=profile_path,
            )

        return LLMAuthResolution(
            mode=LLMAuthMode.CODEX_OAUTH,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message="Codex auth.json is present but does not include a usable tokens.access_token value.",
            source="codex_auth_json",
            profile_name=profile_name,
            profile_path=profile_path,
        )

    profile = _extract_profile(document, profile_name)
    if profile is None:
        return LLMAuthResolution(
            mode=LLMAuthMode.CODEX_OAUTH,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message=f"Auth profile '{profile_name}' not found in profile JSON.",
            source="codex_oauth_profile",
            profile_name=profile_name,
            profile_path=profile_path,
        )

    provider = str(profile.get("provider", "")).strip().lower()
    profile_mode = str(profile.get("type") or profile.get("mode") or "").strip().lower()
    if provider and provider != "openai-codex":
        return LLMAuthResolution(
            mode=LLMAuthMode.CODEX_OAUTH,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message=f"Auth profile '{profile_name}' provider '{provider}' is not supported for codex_oauth mode.",
            source="codex_oauth_profile",
            profile_name=profile_name,
            profile_path=profile_path,
        )
    if profile_mode and profile_mode != "oauth":
        return LLMAuthResolution(
            mode=LLMAuthMode.CODEX_OAUTH,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message=f"Auth profile '{profile_name}' mode '{profile_mode}' is not supported; expected oauth.",
            source="codex_oauth_profile",
            profile_name=profile_name,
            profile_path=profile_path,
        )

    access_token = profile.get("access")
    if not isinstance(access_token, str) or not access_token.strip():
        return LLMAuthResolution(
            mode=LLMAuthMode.CODEX_OAUTH,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message=f"Auth profile '{profile_name}' does not include a usable access token.",
            source="codex_oauth_profile",
            profile_name=profile_name,
            profile_path=profile_path,
        )

    expires_at = _parse_datetime(profile.get("expires")) or _extract_jwt_exp(access_token)
    if expires_at and expires_at <= datetime.now(UTC) + TOKEN_EXPIRY_GRACE_PERIOD:
        return LLMAuthResolution(
            mode=LLMAuthMode.CODEX_OAUTH,
            token=None,
            model_name=model_name,
            base_url=base_url,
            healthy=False,
            message=f"Codex auth profile '{profile_name}' is expired or about to expire.",
            source="codex_oauth_profile",
            expires_at=expires_at,
            profile_name=profile_name,
            profile_path=profile_path,
        )

    message = "Using experimental codex_oauth profile-based token."
    if mode_fallback:
        message = f"{message} Unknown LLM_AUTH_MODE value was provided; codex_oauth selected by parser."

    return LLMAuthResolution(
        mode=LLMAuthMode.CODEX_OAUTH,
        token=access_token,
        model_name=model_name,
        base_url=base_url,
        healthy=True,
        message=message,
        source="codex_oauth_profile",
        expires_at=expires_at,
        profile_name=profile_name,
        profile_path=profile_path,
    )
