"""Configuration via environment variables.

Each inbound direction has its own HMAC secret. A direction whose secret is unset is
treated as disabled and rejects requests fail-closed (see security.py / app.py) — never
as "verification skipped".
"""

from __future__ import annotations

import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Inbound: GitHub -> Vikunja ---------------------------------------
    github_webhook_secret: str = ""  # X-Hub-Signature-256 HMAC key; unset => endpoint disabled
    # Vikunja service credential used to create tasks from GitHub events.
    vikunja_api_url: str = "https://vikunja.helmforge.me"
    vikunja_api_token: str = ""
    # Where GitHub-sourced tasks land. Per-repo overrides win over the default.
    github_default_project_id: int = 0
    github_project_map: dict[str, int] = {}

    # --- Inbound: Vikunja -> Matrix / ntfy --------------------------------
    vikunja_webhook_secret: str = ""  # X-Vikunja-Signature HMAC key; unset => endpoint disabled

    matrix_homeserver: str = "http://127.0.0.1:8008"
    matrix_access_token: str = ""
    matrix_room_id: str = ""  # #vikunja room

    ntfy_url: str = "https://ntfy.glitch42.com"
    ntfy_topic: str = ""
    ntfy_token: str = ""  # optional bearer for a protected ntfy topic

    # --- Server -----------------------------------------------------------
    # Fail-safe default: loopback only. A deployment that needs to be reached by a
    # reverse-proxy container sets HOST explicitly to the interface that proxy uses (on forge,
    # the forge-net bridge gateway — see start.sh / docs/forge.md), never 0.0.0.0.
    host: str = "127.0.0.1"
    port: int = 8502
    request_timeout: float = 10.0

    @field_validator("github_project_map", mode="before")
    @classmethod
    def _parse_map(cls, v: object) -> object:
        """Accept a JSON string (env var) or an already-decoded dict."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return {}
            return json.loads(v)
        return v


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Test hook: drop the cached Settings so the next get_settings() re-reads the env."""
    global _settings
    _settings = None
