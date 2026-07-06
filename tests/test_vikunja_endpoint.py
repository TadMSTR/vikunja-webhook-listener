"""Vikunja → Matrix/ntfy endpoint: signature enforcement and event routing to sinks."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from tests.conftest import sign_vikunja
from vikunja_webhook_listener import app as app_module


@pytest.fixture
def vk_client(set_env, monkeypatch):
    set_env()
    matrix = AsyncMock()
    ntfy = AsyncMock()
    monkeypatch.setattr(app_module, "send_matrix", matrix)
    monkeypatch.setattr(app_module, "send_ntfy", ntfy)
    return TestClient(app_module.app), matrix, ntfy


def _post(client, payload: dict, secret_ok: bool = True):
    body = json.dumps(payload).encode()
    sig = sign_vikunja(body) if secret_ok else "bad"
    return client.post("/webhook/vikunja", content=body, headers={"X-Vikunja-Signature": sig})


def test_task_created_posts_matrix(vk_client):
    client, matrix, ntfy = vk_client
    r = _post(client, {"event_name": "task.created", "data": {"task": {"id": 3, "title": "T"}}})
    assert r.status_code == 200
    assert matrix.await_count == 1 and ntfy.await_count == 0
    assert "created" in matrix.await_args.args[0].lower()


def test_task_updated_done_posts_completion(vk_client):
    client, matrix, _ntfy = vk_client
    r = _post(
        client,
        {"event_name": "task.updated", "data": {"task": {"id": 3, "title": "T", "done": True}}},
    )
    assert r.status_code == 200
    assert "completed" in matrix.await_args.args[0].lower()


def test_reminder_fires_ntfy(vk_client):
    client, matrix, ntfy = vk_client
    r = _post(
        client,
        {"event_name": "task.reminder.fired", "data": {"task": {"id": 9, "title": "Ping"}}},
    )
    assert r.status_code == 200
    assert ntfy.await_count == 1 and matrix.await_count == 0


def test_unhandled_event_acknowledged_no_notify(vk_client):
    client, matrix, ntfy = vk_client
    r = _post(client, {"event_name": "task.attachment.created", "data": {}})
    assert r.status_code == 200
    assert matrix.await_count == 0 and ntfy.await_count == 0


def test_invalid_signature_rejected(vk_client):
    client, matrix, _ntfy = vk_client
    r = _post(client, {"event_name": "task.created", "data": {}}, secret_ok=False)
    assert r.status_code == 401
    assert matrix.await_count == 0


def test_endpoint_disabled_when_secret_unset(set_env, monkeypatch):
    set_env(clear_keys=["VIKUNJA_WEBHOOK_SECRET"])
    monkeypatch.setattr(app_module, "send_matrix", AsyncMock())
    client = TestClient(app_module.app)
    body = json.dumps({"event_name": "task.created", "data": {}}).encode()
    r = client.post("/webhook/vikunja", content=body, headers={"X-Vikunja-Signature": "x"})
    assert r.status_code == 401


def test_health_reports_enabled_directions(vk_client):
    client, _, _ = vk_client
    body = client.get("/health").json()
    assert body["github_inbound"] is True and body["vikunja_inbound"] is True
