"""HMAC signature verification for both inbound directions.

Deliberate deviation from `plane-webhook-listener`, whose `verify_signature()` returns
True (skips verification) when no secret is configured — a fail-*open* soft spot on an
internet-reachable endpoint. Here every check is fail-*closed*: an unset secret is handled
by the caller as "endpoint disabled → reject", and a missing/blank signature never matches.
"""

from __future__ import annotations

import hashlib
import hmac

_GITHUB_PREFIX = "sha256="


def _hexdigest(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_github(body: bytes, signature_header: str, secret: str) -> bool:
    """Verify a GitHub `X-Hub-Signature-256` header (``sha256=<hex>``).

    Callers must confirm ``secret`` is set before calling — an empty secret here returns
    False (never True), so a misordered call still fails closed.
    """
    if not secret or not signature_header.startswith(_GITHUB_PREFIX):
        return False
    expected = _GITHUB_PREFIX + _hexdigest(secret, body)
    return hmac.compare_digest(expected, signature_header)


def verify_vikunja(body: bytes, signature_header: str, secret: str) -> bool:
    """Verify a Vikunja `X-Vikunja-Signature` header (raw hex HMAC-SHA256 of the body)."""
    if not secret or not signature_header:
        return False
    expected = _hexdigest(secret, body)
    return hmac.compare_digest(expected, signature_header)
