"""HMAC verification — the fail-closed security boundary.

The whole reason this repo exists separately from plane-webhook-listener is that its
verify_signature() fails *open* (returns True) when no secret is set. These tests pin the
opposite: no secret, no signature, or a wrong signature must never verify.
"""

from __future__ import annotations

from vikunja_webhook_listener.security import verify_github, verify_vikunja

BODY = b'{"hello":"world"}'
SECRET = "s3cret"


def _gh(body: bytes, secret: str) -> str:
    import hashlib
    import hmac

    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _vk(body: bytes, secret: str) -> str:
    import hashlib
    import hmac

    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# --- GitHub ---------------------------------------------------------------


def test_github_valid_signature():
    assert verify_github(BODY, _gh(BODY, SECRET), SECRET) is True


def test_github_wrong_secret_rejected():
    assert verify_github(BODY, _gh(BODY, "other"), SECRET) is False


def test_github_tampered_body_rejected():
    assert verify_github(b"tampered", _gh(BODY, SECRET), SECRET) is False


def test_github_unset_secret_fails_closed():
    # Even given a signature computed with "", an empty configured secret must not verify.
    assert verify_github(BODY, _gh(BODY, ""), "") is False


def test_github_missing_prefix_rejected():
    raw = _gh(BODY, SECRET).removeprefix("sha256=")
    assert verify_github(BODY, raw, SECRET) is False


def test_github_blank_signature_rejected():
    assert verify_github(BODY, "", SECRET) is False


# --- Vikunja --------------------------------------------------------------


def test_vikunja_valid_signature():
    assert verify_vikunja(BODY, _vk(BODY, SECRET), SECRET) is True


def test_vikunja_wrong_secret_rejected():
    assert verify_vikunja(BODY, _vk(BODY, "other"), SECRET) is False


def test_vikunja_unset_secret_fails_closed():
    assert verify_vikunja(BODY, _vk(BODY, ""), "") is False


def test_vikunja_blank_signature_rejected():
    assert verify_vikunja(BODY, "", SECRET) is False
