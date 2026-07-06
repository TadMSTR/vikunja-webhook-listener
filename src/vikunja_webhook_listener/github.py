"""Parse GitHub webhook payloads into a Vikunja task spec.

Only issue/PR *opened* events produce a task; everything else is ignored upstream.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any


@dataclass
class TaskSpec:
    title: str
    description: str
    repo: str


def _resource(payload: dict[str, Any], event: str) -> dict[str, Any] | None:
    if event == "issues":
        return payload.get("issue")
    if event == "pull_request":
        return payload.get("pull_request")
    return None


def is_actionable(payload: dict[str, Any], event: str) -> bool:
    """True only for a newly opened issue or PR."""
    return event in {"issues", "pull_request"} and payload.get("action") == "opened"


def to_task_spec(payload: dict[str, Any], event: str) -> TaskSpec | None:
    """Build a TaskSpec from an opened issue/PR payload, or None if not applicable."""
    if not is_actionable(payload, event):
        return None
    res = _resource(payload, event)
    if not res:
        return None

    repo = payload.get("repository", {}).get("full_name", "unknown/unknown")
    number = res.get("number", "?")
    title = res.get("title", "(untitled)")
    url = res.get("html_url", "")
    author = res.get("user", {}).get("login", "unknown")
    body = (res.get("body") or "").strip()
    kind = "PR" if event == "pull_request" else "issue"

    # SECURITY (audit F-1): title/body/author come from the issue/PR author — an arbitrary
    # internet user on a public repo. The description is stored and rendered as HTML in the
    # Vikunja UI, so escape every free-text field before interpolation rather than relying on
    # Vikunja's server-side sanitizer as the only barrier. `quote=True` also neutralizes the
    # `"` that would otherwise break out of the href attribute.
    e_author = html.escape(author)
    e_repo = html.escape(repo)
    e_url = html.escape(url, quote=True)
    e_body = html.escape(body)

    description = (
        f"<p>Opened by <strong>{e_author}</strong> as a GitHub {kind}: "
        f'<a href="{e_url}">{e_repo}#{number}</a></p>'
    )
    if e_body:
        description += f"<hr><p>{e_body}</p>"

    # Task title is plain text in Vikunja (not HTML), but keep the raw title here — escaping
    # would show literal entities in the title field. The description is the HTML-rendered sink.
    return TaskSpec(title=f"[{repo}#{number}] {title}", description=description, repo=repo)
