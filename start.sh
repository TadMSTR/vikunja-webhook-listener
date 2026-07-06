#!/usr/bin/env bash
# Load secrets from env files and start the webhook listener.
# Secrets NEVER live in this repo or in ecosystem.config.cjs — they are sourced here at
# runtime from ~/.secrets/ (chmod 600), same pattern as plane-webhook-listener.
set -euo pipefail
set -a

# Matrix credentials (MATRIX_HOMESERVER / MATRIX_ACCESS_TOKEN / MATRIX_ROOM_ID via remap below)
source ~/.secrets/matrix-forge.env

# Listener-specific secrets: GITHUB_WEBHOOK_SECRET, VIKUNJA_WEBHOOK_SECRET,
# VIKUNJA_API_TOKEN, NTFY_TOPIC/NTFY_TOKEN, GITHUB_DEFAULT_PROJECT_ID, GITHUB_PROJECT_MAP.
source ~/.secrets/vikunja-webhook.env

set +a

# Point the listener at the #vikunja room and the forge homeserver.
export MATRIX_ROOM_ID="${MATRIX_ROOM_ID:-${MATRIX_ROOM_VIKUNJA:-}}"
export MATRIX_HOMESERVER="${MATRIX_HOMESERVER:-${MATRIX_HOMESERVER_URL:-http://127.0.0.1:8008}}"
export PORT="${PORT:-8502}"

exec /opt/venvs/vikunja-webhook-listener/bin/vikunja-webhook-listener
