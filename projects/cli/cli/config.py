from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StrictHttpUrl(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: str, info) -> "StrictHttpUrl":
        if not isinstance(v, str):
            raise ValueError("URL must be a string")

        # Parse the URL
        parsed = urlparse(v)

        # Check for query/fragment
        if parsed.query or parsed.fragment:
            raise ValueError("URL cannot contain query parameters or fragments")

        # Ensure it's http/https
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must use HTTP or HTTPS protocol")

        # Ensure there's a netloc (domain)
        if not parsed.netloc:
            raise ValueError("URL must contain a valid domain")

        # Store without trailing slash
        return cls(v.rstrip("/"))

    def __str__(self) -> str:
        return self.rstrip("/")

    def __repr__(self) -> str:
        return f"StrictHttpUrl('{self.rstrip('/')}')"


class PasswordCredential(BaseConfig):
    username: str
    password: str


class TokenCredential(BaseConfig):
    token: str


class NemesisConfig(BaseConfig):
    url: StrictHttpUrl
    credential: PasswordCredential
    expiration_days: Annotated[int, Field(gt=0, description="Days until uploaded files are deleted")] = 100
    max_file_size: Annotated[int, Field(gt=0, description="Maximum file size in bytes")] = 1_000_000_000


class MythicConfig(BaseConfig):
    url: StrictHttpUrl
    credential: PasswordCredential | TokenCredential

    @field_validator("credential")
    @classmethod
    def validate_credential(cls, v):
        if isinstance(v, dict):
            if "token" in v:
                return TokenCredential(**v)
            return PasswordCredential(**v)
        return v


class OutflankConfig(BaseConfig):
    url: StrictHttpUrl
    credential: PasswordCredential
    downloads_dir_path: Path | None = Field(
        None,
        description="Optional: Path to Outflank C2's upload directory where files will be pulled from instead of the Outflank API",
    )
    poll_interval_sec: Annotated[int, Field(gt=0, description="Polling interval of the Outflank API in seconds")] = 3

    @field_validator("downloads_dir_path")
    @classmethod
    def validate_path(cls, v):
        if v is None:
            return None
        return Path(v)


class CobaltStrikeConfig(BaseConfig):
    url: StrictHttpUrl
    credential: PasswordCredential
    project: str = Field(description="Project name for Nemesis file uploads")
    poll_interval_sec: Annotated[
        int, Field(gt=0, description="Polling interval of the Cobalt Strike API in seconds")
    ] = 3


class Config(BaseConfig):
    cache_db_path: Path = Field(default_factory=lambda: Path("/tmp/connectors"), description="LevelDB cache path")
    conn_timeout_sec: Annotated[int, Field(gt=0, description="Connection timeout in seconds")] = 30
    validate_https_certs: bool = Field(True, description="Whether to validate HTTPS certificates")

    nemesis: NemesisConfig
    mythic: list[MythicConfig] | None = Field(default_factory=list)
    outflank: list[OutflankConfig] | None = Field(default_factory=list)
    cobaltstrike: list[CobaltStrikeConfig] | None = Field(default_factory=list)

    @field_validator("mythic", "outflank", "cobaltstrike", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        elif isinstance(v, dict):
            return [v]
        return v

    @field_validator("cache_db_path", mode="before")
    @classmethod
    def validate_cache_path(cls, v):
        return Path(v)


def load_config(config_path: str) -> Config:
    """Load and validate configuration from YAML file"""
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)
    return Config(**config_dict)


CONNECTOR_ALIASES = {
    "outflank": "outflank",
    "connect-outflank": "outflank",
    "connect_outflank": "outflank",
    "mythic": "mythic",
    "connect-mythic": "mythic",
    "connect_mythic": "mythic",
    "cobaltstrike": "cobaltstrike",
    "connect-cobaltstrike": "cobaltstrike",
    "connect_cobaltstrike": "cobaltstrike",
}


def resolve_connector_name(connector: str) -> str:
    """Normalize connector names from CLI command aliases to Config field names."""
    key = connector.strip().lower()
    if key not in CONNECTOR_ALIASES:
        valid = ", ".join(sorted(CONNECTOR_ALIASES))
        raise ValueError(f"Unknown connector '{connector}'. Expected one of: {valid}")
    return CONNECTOR_ALIASES[key]


def validate_connector_config(config: Config, connector: str) -> None:
    """Validate connector section presence and critical connector-specific fields."""
    connector_name = resolve_connector_name(connector)
    connector_entries = getattr(config, connector_name)

    if not connector_entries:
        raise ValueError(
            f"Config preflight failed: no '{connector_name}' connector entries were found in the YAML file."
        )

    if connector_name == "outflank":
        for idx, outflank_cfg in enumerate(connector_entries):
            if outflank_cfg.downloads_dir_path is not None and not str(outflank_cfg.downloads_dir_path).strip():
                raise ValueError(f"Config preflight failed: outflank[{idx}].downloads_dir_path cannot be empty.")

    if connector_name == "cobaltstrike":
        for idx, cobalt_cfg in enumerate(connector_entries):
            if not cobalt_cfg.project.strip():
                raise ValueError(f"Config preflight failed: cobaltstrike[{idx}].project cannot be empty.")


def load_connector_config(config_path: str, connector: str) -> Config:
    """Load config and run connector-specific preflight checks."""
    config = load_config(config_path)
    validate_connector_config(config, connector)
    return config
