"""Outbound notification sinks: Matrix room messages and ntfy push."""

from __future__ import annotations

import time

import httpx
import structlog

from .config import get_settings

log = structlog.get_logger()


async def send_matrix(message: str) -> None:
    """Post a plain-text message to the configured Matrix room.

    Missing Matrix config is logged and skipped rather than raised — a webhook delivery
    should still succeed (Vikunja does not retry) even if the chat sink is misconfigured.
    """
    cfg = get_settings()
    if not cfg.matrix_access_token or not cfg.matrix_room_id:
        log.warning("matrix_not_configured", preview=message[:80])
        return
    txn = f"vikunja-wh-{int(time.time() * 1000)}"
    url = (
        f"{cfg.matrix_homeserver.rstrip('/')}"
        f"/_matrix/client/v3/rooms/{cfg.matrix_room_id}/send/m.room.message/{txn}"
    )
    try:
        async with httpx.AsyncClient(timeout=cfg.request_timeout) as client:
            resp = await client.put(
                url,
                headers={"Authorization": f"Bearer {cfg.matrix_access_token}"},
                json={"msgtype": "m.text", "body": message},
            )
            resp.raise_for_status()
        log.info("matrix_sent", room=cfg.matrix_room_id)
    except httpx.HTTPError as exc:
        log.error("matrix_send_failed", error=str(exc))


async def send_ntfy(title: str, message: str, tags: str = "bell") -> None:
    """Publish a push notification to the configured ntfy topic (best-effort)."""
    cfg = get_settings()
    if not cfg.ntfy_topic:
        log.warning("ntfy_not_configured", preview=title[:80])
        return
    url = f"{cfg.ntfy_url.rstrip('/')}/{cfg.ntfy_topic}"
    headers = {"Title": title, "Tags": tags}
    if cfg.ntfy_token:
        headers["Authorization"] = f"Bearer {cfg.ntfy_token}"
    try:
        async with httpx.AsyncClient(timeout=cfg.request_timeout) as client:
            resp = await client.post(url, headers=headers, content=message.encode("utf-8"))
            resp.raise_for_status()
        log.info("ntfy_sent", topic=cfg.ntfy_topic)
    except httpx.HTTPError as exc:
        log.error("ntfy_send_failed", error=str(exc))
