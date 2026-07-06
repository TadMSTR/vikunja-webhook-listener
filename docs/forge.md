# Forge deployment

Deploy + wiring for `vikunja-webhook-listener` — Phase 10/11 of `vikunja-migration-2026-07`.

## PM2

```bash
python -m venv /opt/venvs/vikunja-webhook-listener
/opt/venvs/vikunja-webhook-listener/bin/pip install /home/ted/repos/personal/vikunja-webhook-listener
pm2 start ecosystem.config.cjs && pm2 save
curl -s http://127.0.0.1:8502/health
```

`start.sh` sources secrets from `~/.secrets/` at runtime — create
`~/.secrets/vikunja-webhook.env` (chmod 600) with:

```bash
GITHUB_WEBHOOK_SECRET=...          # unset => /webhook/github returns 401 (disabled)
VIKUNJA_WEBHOOK_SECRET=...         # unset => /webhook/vikunja returns 401 (disabled)
VIKUNJA_API_TOKEN=...              # dedicated least-privilege Vikunja account (see below)
GITHUB_DEFAULT_PROJECT_ID=<id>
GITHUB_PROJECT_MAP={"TadMSTR/vikunja-mcp": <id>, ...}
NTFY_TOPIC=<topic>
# NTFY_TOKEN=...                   # only if the ntfy topic is protected
```

Port `8502` (confirmed free 2026-07-06; re-check at deploy). Bound `0.0.0.0` so the SWAG
container can reach the host process — same pattern as `plane-webhook-listener`.

## SWAG vhost

Expose a public hostname (e.g. `vikunja-hooks.helmforge.me`) proxying to the listener.
Do **not** put Authentik forward-auth in front of it — GitHub and Vikunja cannot complete a
browser redirect. The HMAC signatures are the authentication.

## Vikunja service token (GitHub → task creation)

`VIKUNJA_API_TOKEN` needs a Vikunja account with create rights on the target project(s).
The build provisioned 5 per-agent tokens but **no dedicated webhook-bot token** — sysadmin
should create one (e.g. `agent-webhook` at `secret/data/vikunja/agent-webhook`) or the
listener can reuse an existing agent token. Flag for Phase 11.

## Registering the webhooks

### GitHub → listener (per code repo)
Add a webhook in each tracked GitHub repo: payload URL = the SWAG vhost `/webhook/github`,
content-type `application/json`, secret = `GITHUB_WEBHOOK_SECRET`, events = Issues + Pull
requests. GitHub sends a `ping` on creation (the listener 200s it).

### Vikunja → listener
- **Project events** (`task.created`, `task.updated`, `task.comment.created`): register a
  **project** webhook via `vikunja-mcp`'s `webhook_create` (target = SWAG vhost
  `/webhook/vikunja`, secret = `VIKUNJA_WEBHOOK_SECRET`, events as needed). Target URL must be
  public (Vikunja rejects RFC1918 — SSRF guard).
- **Reminders / overdue** (`task.reminder.fired`, `task.overdue`, `tasks.overdue`): these are
  **user** webhooks, not project webhooks. They must be registered at
  `PUT /api/v1/user/settings/webhooks` for each user whose reminders should push to ntfy.
  `vikunja-mcp`'s `webhook_create` only covers project webhooks today — registering user
  webhooks is a follow-up (add user-webhook tools to vikunja-mcp, or configure in the UI).

## Notes / corrections vs the build plan

- No `task.done` event exists — completion is detected from `task.updated` with `done: true`.
- The plan's `task.reminder` is really `task.reminder.fired` and is a user webhook.
