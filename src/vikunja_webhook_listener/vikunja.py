"""Create Vikunja tasks from GitHub events, using the listener's service token."""

from __future__ import annotations

import httpx
import structlog

from .config import get_settings
from .github import TaskSpec

log = structlog.get_logger()


class VikunjaError(RuntimeError):
    """Task creation against the Vikunja API failed."""


def _project_for(repo: str) -> int:
    cfg = get_settings()
    return cfg.github_project_map.get(repo, cfg.github_default_project_id)


async def create_task(spec: TaskSpec) -> dict:
    """Create a task in the project mapped to spec.repo (or the default project).

    Raises:
        VikunjaError: if no service token is configured, no target project resolves, or
            the API rejects the request.
    """
    cfg = get_settings()
    if not cfg.vikunja_api_token:
        raise VikunjaError("VIKUNJA_API_TOKEN is not set; cannot create tasks from GitHub events")

    project_id = _project_for(spec.repo)
    if project_id <= 0:
        raise VikunjaError(
            f"No Vikunja project mapped for {spec.repo!r} and no valid GITHUB_DEFAULT_PROJECT_ID"
        )

    url = f"{cfg.vikunja_api_url.rstrip('/')}/api/v1/projects/{project_id}/tasks"
    headers = {"Authorization": f"Bearer {cfg.vikunja_api_token}"}
    body = {"title": spec.title, "description": spec.description}
    async with httpx.AsyncClient(timeout=cfg.request_timeout) as client:
        resp = await client.put(url, headers=headers, json=body)
    if resp.status_code >= 400:
        raise VikunjaError(f"Vikunja API {resp.status_code}: {resp.text[:200]}")
    task = resp.json()
    log.info("vikunja_task_created", project_id=project_id, task_id=task.get("id"), repo=spec.repo)
    return task
