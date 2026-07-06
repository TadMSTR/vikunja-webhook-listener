# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial `vikunja-webhook-listener` FastAPI service.
- `POST /webhook/github`: opened GitHub issue/PR → Vikunja task (per-repo project mapping).
- `POST /webhook/vikunja`: Vikunja events → Matrix room and ntfy push.
- Fail-closed HMAC verification for both directions (`X-Hub-Signature-256`,
  `X-Vikunja-Signature`); an unset secret disables its endpoint with `401` — the deliberate
  fix for `plane-webhook-listener`'s fail-open `verify_signature()`.
- Event routing verified against Vikunja docs: completion via `task.updated` (`done: true`),
  reminders via the `task.reminder.fired` / `*.overdue` user-webhook events.
- CI (lint + matrix tests 3.11–3.13, coverage floor 80%) with SHA-pinned actions.
