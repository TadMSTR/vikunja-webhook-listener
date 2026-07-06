"""GitHub → Vikunja endpoint: signature enforcement, event filtering, create flow."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from tests.conftest import sign_github
from vikunja_webhook_listener import app as app_module
from vikunja_webhook_listener.vikunja import VikunjaError


@pytest.fixture
def gh_client(set_env, monkeypatch):
    set_env()
    mock = AsyncMock(return_value={"id": 1})
    monkeypatch.setattr(app_module, "create_task", mock)
    return TestClient(app_module.app), mock


def _issue_opened() -> bytes:
    return json.dumps(
        {
            "action": "opened",
            "issue": {
                "number": 12,
                "title": "Bug",
                "html_url": "http://gh/12",
                "user": {"login": "ted"},
            },
            "repository": {"full_name": "TadMSTR/vikunja-mcp"},
        }
    ).encode()


def _post(client, body, sig, event="issues"):
    return client.post(
        "/webhook/github",
        content=body,
        headers={"X-Hub-Signature-256": sig, "X-GitHub-Event": event},
    )


def test_opened_issue_creates_task(gh_client):
    client, mock = gh_client
    body = _issue_opened()
    r = _post(client, body, sign_github(body))
    assert r.status_code == 200
    assert mock.await_count == 1
    spec = mock.await_args.args[0]
    assert spec.title == "[TadMSTR/vikunja-mcp#12] Bug"


def test_invalid_signature_rejected(gh_client):
    client, mock = gh_client
    body = _issue_opened()
    r = _post(client, body, "sha256=deadbeef")
    assert r.status_code == 401
    assert mock.await_count == 0


def test_ping_event_acknowledged_without_task(gh_client):
    client, mock = gh_client
    body = b"{}"
    r = _post(client, body, sign_github(body), event="ping")
    assert r.status_code == 200
    assert mock.await_count == 0


def test_non_opened_action_ignored(gh_client):
    client, mock = gh_client
    body = json.dumps({"action": "closed", "issue": {"number": 1}}).encode()
    r = _post(client, body, sign_github(body))
    assert r.status_code == 200
    assert mock.await_count == 0


def test_downstream_failure_returns_502(gh_client):
    client, mock = gh_client
    mock.side_effect = VikunjaError("boom")
    body = _issue_opened()
    r = _post(client, body, sign_github(body))
    assert r.status_code == 502


def test_endpoint_disabled_when_secret_unset(set_env, monkeypatch):
    set_env(clear_keys=["GITHUB_WEBHOOK_SECRET"])
    monkeypatch.setattr(app_module, "create_task", AsyncMock())
    client = TestClient(app_module.app)
    body = _issue_opened()
    r = _post(client, body, sign_github(body))
    assert r.status_code == 401  # fail closed, not "skip verification"
