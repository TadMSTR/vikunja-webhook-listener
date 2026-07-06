"""Outbound HTTP behaviour for the notify + vikunja modules (respx-mocked)."""

from __future__ import annotations

import httpx
import pytest
import respx

from vikunja_webhook_listener import notify, vikunja
from vikunja_webhook_listener.github import TaskSpec
from vikunja_webhook_listener.vikunja import VikunjaError


@respx.mock
async def test_create_task_puts_to_mapped_project(set_env):
    set_env({"GITHUB_PROJECT_MAP": '{"org/repo": 42}'})
    route = respx.put("https://vikunja.test/api/v1/projects/42/tasks").mock(
        return_value=httpx.Response(200, json={"id": 7})
    )
    task = await vikunja.create_task(TaskSpec(title="t", description="d", repo="org/repo"))
    assert task["id"] == 7
    assert route.calls.last.request.headers["authorization"] == "Bearer svc-token"


@respx.mock
async def test_create_task_falls_back_to_default_project(set_env):
    set_env()  # default project 5, no map
    route = respx.put("https://vikunja.test/api/v1/projects/5/tasks").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    await vikunja.create_task(TaskSpec(title="t", description="d", repo="unmapped/repo"))
    assert route.called


async def test_create_task_without_token_raises(set_env):
    set_env(clear_keys=["VIKUNJA_API_TOKEN"])
    with pytest.raises(VikunjaError):
        await vikunja.create_task(TaskSpec(title="t", description="d", repo="x/y"))


async def test_create_task_without_project_raises(set_env):
    set_env({"GITHUB_DEFAULT_PROJECT_ID": "0"})
    with pytest.raises(VikunjaError):
        await vikunja.create_task(TaskSpec(title="t", description="d", repo="x/y"))


@respx.mock
async def test_create_task_api_error_raises(set_env):
    set_env()
    respx.put("https://vikunja.test/api/v1/projects/5/tasks").mock(
        return_value=httpx.Response(403, text="forbidden")
    )
    with pytest.raises(VikunjaError):
        await vikunja.create_task(TaskSpec(title="t", description="d", repo="x/y"))


@respx.mock
async def test_send_matrix_puts_message(set_env):
    set_env()
    route = respx.put(url__regex=r"http://matrix\.test/_matrix/.*").mock(
        return_value=httpx.Response(200, json={})
    )
    await notify.send_matrix("hello")
    assert route.called


async def test_send_matrix_skips_when_unconfigured(set_env):
    set_env(clear_keys=["MATRIX_ACCESS_TOKEN"])
    # No respx route registered — if it tried to call out, it would error. It must skip.
    await notify.send_matrix("hello")


@respx.mock
async def test_send_ntfy_posts(set_env):
    set_env()
    route = respx.post("https://ntfy.test/vikunja").mock(return_value=httpx.Response(200))
    await notify.send_ntfy("title", "msg")
    assert route.called
    assert route.calls.last.request.headers["Title"] == "title"


async def test_send_ntfy_skips_without_topic(set_env):
    set_env(clear_keys=["NTFY_TOPIC"])
    await notify.send_ntfy("t", "m")
