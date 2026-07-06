"""FastAPI app: GitHub → Vikunja task creation, and Vikunja → Matrix/ntfy notifications.

Both inbound endpoints are internet-reachable (behind SWAG), so each verifies an HMAC
signature and fails closed when its secret is unset — no unauthenticated path exists.
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Header, HTTPException, Request, Response

from . import __version__, events, github
from .config import get_settings
from .notify import send_matrix, send_ntfy
from .security import verify_github, verify_vikunja
from .vikunja import VikunjaError, create_task

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

app = FastAPI(title="vikunja-webhook-listener", version=__version__)


@app.get("/health")
async def health() -> dict:
    cfg = get_settings()
    return {
        "status": "ok",
        "github_inbound": bool(cfg.github_webhook_secret),
        "vikunja_inbound": bool(cfg.vikunja_webhook_secret),
    }


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
) -> Response:
    cfg = get_settings()
    # Fail closed: an unset secret disables this endpoint rather than skipping verification.
    if not cfg.github_webhook_secret:
        raise HTTPException(status_code=401, detail="GitHub webhook secret not configured")

    body = await request.body()
    if not verify_github(body, x_hub_signature_256, cfg.github_webhook_secret):
        log.warning("github_invalid_signature", gh_event=x_github_event)
        raise HTTPException(status_code=401, detail="Invalid signature")

    if x_github_event == "ping":
        return Response(status_code=200)

    payload = await request.json()
    spec = github.to_task_spec(payload, x_github_event)
    if spec is None:
        return Response(status_code=200)  # not an opened issue/PR — acknowledged, ignored

    try:
        await create_task(spec)
    except VikunjaError as exc:
        # 502: we authenticated the caller, but the downstream create failed.
        log.error("github_task_create_failed", error=str(exc), repo=spec.repo)
        raise HTTPException(status_code=502, detail="Failed to create Vikunja task") from exc
    return Response(status_code=200)


@app.post("/webhook/vikunja")
async def vikunja_webhook(
    request: Request,
    x_vikunja_signature: str = Header(default=""),
) -> Response:
    cfg = get_settings()
    if not cfg.vikunja_webhook_secret:
        raise HTTPException(status_code=401, detail="Vikunja webhook secret not configured")

    body = await request.body()
    if not verify_vikunja(body, x_vikunja_signature, cfg.vikunja_webhook_secret):
        log.warning("vikunja_invalid_signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_name = payload.get("event_name", "")
    data = payload.get("data", {})
    if not isinstance(data, dict):
        data = {}

    note = events.route(event_name, data)
    if note.matrix:
        await send_matrix(note.matrix)
    if note.ntfy:
        await send_ntfy(*note.ntfy)
    if not note.matrix and not note.ntfy:
        log.info("vikunja_event_unhandled", vikunja_event=event_name)
    return Response(status_code=200)
