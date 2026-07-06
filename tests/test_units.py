"""Unit tests for payload parsing and event routing (no HTTP)."""

from __future__ import annotations

from vikunja_webhook_listener import events, github


def test_to_task_spec_from_pull_request():
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 4,
            "title": "Add x",
            "html_url": "http://gh/4",
            "user": {"login": "ted"},
            "body": "details",
        },
        "repository": {"full_name": "org/repo"},
    }
    spec = github.to_task_spec(payload, "pull_request")
    assert spec is not None
    assert spec.title == "[org/repo#4] Add x"
    assert "details" in spec.description
    assert spec.repo == "org/repo"


def test_to_task_spec_escapes_html_from_untrusted_payload():
    # Audit F-1: title/body come from an arbitrary internet user on a public repo. A crafted
    # body must not reach the HTML description un-neutralized.
    payload = {
        "action": "opened",
        "issue": {
            "number": 1,
            "title": "pwn",
            "html_url": 'http://gh/1"onmouseover="x',
            "user": {"login": "attacker"},
            "body": "<img src=x onerror=alert(1)> <script>evil()</script>",
        },
        "repository": {"full_name": "org/repo"},
    }
    spec = github.to_task_spec(payload, "issues")
    assert spec is not None
    assert "<script>" not in spec.description
    assert "<img" not in spec.description
    assert "&lt;script&gt;" in spec.description
    # The href must not be breakable via a quote in the URL.
    assert '"onmouseover=' not in spec.description


def test_to_task_spec_ignores_non_opened():
    assert github.to_task_spec({"action": "edited", "issue": {}}, "issues") is None


def test_to_task_spec_ignores_unrelated_event():
    assert github.to_task_spec({"action": "opened"}, "push") is None


def test_route_created():
    n = events.route("task.created", {"task": {"id": 1, "title": "A"}})
    assert n.matrix and "created" in n.matrix.lower()
    assert n.ntfy is None


def test_route_updated_not_done_is_silent():
    n = events.route("task.updated", {"task": {"id": 1, "title": "A", "done": False}})
    assert n.matrix is None and n.ntfy is None


def test_route_comment():
    n = events.route(
        "task.comment.created",
        {"task": {"id": 1, "title": "A"}, "comment": {"author": {"username": "bob"}}},
    )
    assert "bob" in n.matrix


def test_route_overdue_goes_to_ntfy():
    n = events.route("task.overdue", {"task": {"id": 2, "title": "Late"}})
    assert n.ntfy is not None and n.matrix is None
    assert "Overdue" in n.ntfy[0]


def test_route_unknown_event_empty():
    n = events.route("project.deleted", {})
    assert n.matrix is None and n.ntfy is None
