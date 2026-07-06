# Security

## Threat model

Both endpoints are reachable from the public internet (Vikunja's webhook SSRF guard requires
public target hostnames, and GitHub delivers from its own ranges). The only authentication is
HMAC signature verification, so it must be **fail-closed** everywhere:

- **Unset secret ⇒ endpoint disabled.** If `GITHUB_WEBHOOK_SECRET` (or
  `VIKUNJA_WEBHOOK_SECRET`) is unset, that endpoint returns `401` for every request. It never
  falls through to "verification skipped" — the explicit departure from
  `plane-webhook-listener`.
- **Signature verified over raw bytes**, before JSON parsing, using `hmac.compare_digest`
  (constant-time). Missing or malformed signatures never match.
- GitHub: `X-Hub-Signature-256` (`sha256=<hex>`). Vikunja: `X-Vikunja-Signature` (raw hex).

## Secrets

No secret is committed. `start.sh` sources them at runtime from `~/.secrets/` (chmod 600):
webhook HMAC secrets, the Vikunja service token, Matrix token, and ntfy token. The Vikunja
service token that creates GitHub-sourced tasks should be a dedicated, least-privilege
Vikunja account scoped to the target project(s).

## Non-goals

- No replay protection beyond HMAC (Vikunja/GitHub deliver once; no nonce store).
- Notification sinks (Matrix/ntfy) are best-effort and do not gate the 200 response.

## Reporting

Personal homelab project — report via the repository issue tracker.
