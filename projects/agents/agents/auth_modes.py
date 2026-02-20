"""Supported runtime LLM authentication modes."""

from enum import StrEnum


class LLMAuthMode(StrEnum):
    OFFICIAL_KEY = "official_key"
    CODEX_OAUTH = "codex_oauth"

    @classmethod
    def parse(cls, value: str | None) -> tuple["LLMAuthMode", bool]:
        """
        Parse an auth mode from environment input.

        Returns:
            (mode, fallback_used) where fallback_used indicates an invalid value
            was provided and the default mode was used.
        """
        if not value:
            return cls.OFFICIAL_KEY, False

        normalized = value.strip().lower()
        try:
            return cls(normalized), False
        except ValueError:
            return cls.OFFICIAL_KEY, True
