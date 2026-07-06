"""Route a Vikunja webhook event to a Matrix message and/or an ntfy push.

Notes on event names (verified against Vikunja's docs, not the original build plan):
  * There is no `task.done` event — completion arrives as `task.updated` with the task's
    `done` field true.
  * Reminders are `task.reminder.fired` (a *user* webhook event), not `task.reminder`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import get_settings

_NTFY_EVENTS = {"task.reminder.fired", "task.overdue", "tasks.overdue"}


@dataclass
class Notification:
    matrix: str | None = None
    ntfy: tuple[str, str] | None = None  # (title, message)


def _task_url(task_id: Any) -> str:
    base = get_settings().vikunja_api_url.rstrip("/")
    return f"{base}/tasks/{task_id}" if task_id else base


def _task(data: dict[str, Any]) -> dict[str, Any]:
    t = data.get("task")
    return t if isinstance(t, dict) else {}


def route(event_name: str, data: dict[str, Any]) -> Notification:
    """Map an event to the notifications it should produce (may be empty)."""
    task = _task(data)
    title = task.get("title", "(untitled)")
    tid = task.get("id")
    url = _task_url(tid)

    if event_name == "task.created":
        return Notification(matrix=f"[VIKUNJA] Task created: {title}\n{url}")

    if event_name == "task.updated" and task.get("done") is True:
        return Notification(matrix=f"[VIKUNJA] Task completed ✓: {title}\n{url}")

    if event_name == "task.comment.created":
        comment = data.get("comment", {})
        author = comment.get("author", {}).get("username", "someone") if comment else "someone"
        return Notification(matrix=f"[VIKUNJA] Comment by {author} on: {title}\n{url}")

    if event_name in _NTFY_EVENTS:
        label = "Reminder" if event_name == "task.reminder.fired" else "Overdue"
        return Notification(ntfy=(f"Vikunja {label}: {title}", url))

    return Notification()  # unhandled event → acknowledged but no notification
