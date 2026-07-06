"""Shared fixtures: env-configured settings and a FastAPI TestClient."""

from __future__ import annotations

import hashlib
import hmac

import pytest

GITHUB_SECRET = "gh-secret"
VIKUNJA_SECRET = "vk-secret"

BASE_ENV = {
    "GITHUB_WEBHOOK_SECRET": GITHUB_SECRET,
    "VIKUNJA_WEBHOOK_SECRET": VIKUNJA_SECRET,
    "VIKUNJA_API_URL": "https://vikunja.test",
    "VIKUNJA_API_TOKEN": "svc-token",
    "GITHUB_DEFAULT_PROJECT_ID": "5",
    "MATRIX_ACCESS_TOKEN": "mat-token",
    "MATRIX_ROOM_ID": "!vikunja:helmforge.me",
    "MATRIX_HOMESERVER": "http://matrix.test",
    "NTFY_URL": "https://ntfy.test",
    "NTFY_TOPIC": "vikunja",
}


def sign_github(body: bytes, secret: str = GITHUB_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def sign_vikunja(body: bytes, secret: str = VIKUNJA_SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def set_env(monkeypatch):
    """Apply an env dict (BASE_ENV plus overrides) and reset cached settings."""

    def _apply(overrides: dict | None = None, clear_keys: list[str] | None = None):
        from vikunja_webhook_listener import config

        env = dict(BASE_ENV)
        if overrides:
            env.update(overrides)
        for k in clear_keys or []:
            env.pop(k, None)
            monkeypatch.delenv(k, raising=False)
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        config.reset_settings()

    yield _apply
    from vikunja_webhook_listener import config

    config.reset_settings()


@pytest.fixture
def client(set_env):
    """A TestClient with BASE_ENV applied (both directions enabled)."""
    from fastapi.testclient import TestClient

    from vikunja_webhook_listener.app import app

    set_env()
    return TestClient(app)
