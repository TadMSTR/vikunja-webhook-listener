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

# NE-03: bind to the forge-net bridge gateway, not 0.0.0.0. This IP (the host's address on
# the forge-net bridge, subnet 172.20.1.0/24) is reachable by the SWAG container but is NOT
# on the LAN, so the port is never LAN-exposed. SWAG must proxy_pass to this IP by address,
# not the helmforge.me hostname (which resolves to the LAN IP and hits forge's hairpin-NAT).
export HOST="${HOST:-172.20.1.1}"

exec /opt/venvs/vikunja-webhook-listener/bin/vikunja-webhook-listener
