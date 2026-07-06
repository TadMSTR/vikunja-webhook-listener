# AGENTS.md — vikunja-webhook-listener

Operating contract for Claude sessions working in this repo.

## What this service does

Two independent inbound webhook directions in one FastAPI app:
- `POST /webhook/github` — opened GitHub issue/PR → Vikunja task.
- `POST /webhook/vikunja` — Vikunja event → Matrix room and/or ntfy.

## Module boundaries

| Module | Responsibility |
|--------|----------------|
| `config.py` | Env settings; per-direction secrets; repo→project map |
| `security.py` | HMAC verification for both directions — **fail closed** |
| `github.py` | Parse GitHub payload → `TaskSpec` (pure, no I/O) |
| `vikunja.py` | Create a task via the Vikunja API using the service token |
| `events.py` | Map a Vikunja event → `Notification` (pure, no I/O) |
| `notify.py` | Outbound Matrix + ntfy (best-effort, never raises) |
| `app.py` | FastAPI endpoints; wiring + HTTP status decisions |

## Invariants (do not break)

1. **Fail closed, always.** This repo exists *because* `plane-webhook-listener` fails open
   (`main.py:86` returns `True` when the secret is unset). Never reintroduce that. An unset
   secret disables its endpoint (`401`); a missing/blank signature never verifies.
   `tests/test_security.py` and the `*_endpoint_disabled_when_secret_unset` tests guard this.
2. **Verify before parsing.** Compute the HMAC over the raw request body *before* JSON
   parsing — signatures are over bytes, and re-serialized JSON won't match.
3. **Notifications are best-effort.** `notify.py` swallows send failures (logged) so a
   webhook delivery still returns 200 — Vikunja does **not** retry failed deliveries.
4. **Task creation failure is a 502**, not a 200 — the caller authenticated but the
   downstream create failed, and a silent 200 would hide dropped tasks.

## Event-name facts (verified vs Vikunja docs, not the build plan)

- No `task.done` event — completion is `task.updated` with the task `done: true`.
- Reminders are `task.reminder.fired` (a **user** webhook), plus `task.overdue` /
  `tasks.overdue`. Project webhooks cannot emit these.

## Test expectations

- `pytest --cov=vikunja_webhook_listener` — 80% floor (in `pyproject.toml`).
- Security negatives in `tests/test_security.py` are mandatory; never delete to ease coverage.
- Add an endpoint test when adding a route; add an `events.route` case when handling a new
  Vikunja event.

<!-- SECURITY[control]: Both endpoints are internet-reachable behind SWAG. HMAC verification
is the only authentication; it must remain fail-closed. Secrets are sourced at runtime from
~/.secrets/ via start.sh and never committed. -->
