"""Entry point: run the FastAPI app under uvicorn."""

from __future__ import annotations

import structlog
import uvicorn

from . import __version__
from .config import get_settings

log = structlog.get_logger()


def main() -> None:
    cfg = get_settings()
    if not cfg.github_webhook_secret:
        log.warning("github_inbound_disabled", reason="GITHUB_WEBHOOK_SECRET unset")
    if not cfg.vikunja_webhook_secret:
        log.warning("vikunja_inbound_disabled", reason="VIKUNJA_WEBHOOK_SECRET unset")
    log.info("vikunja_webhook_listener_start", version=__version__, host=cfg.host, port=cfg.port)
    uvicorn.run("vikunja_webhook_listener.app:app", host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
