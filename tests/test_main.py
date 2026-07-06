"""Entry point: main() wires uvicorn with the configured host/port."""

from __future__ import annotations

from unittest.mock import MagicMock


def test_main_invokes_uvicorn(set_env, monkeypatch):
    set_env({"PORT": "8502"})
    from vikunja_webhook_listener import __main__

    run = MagicMock()
    monkeypatch.setattr(__main__.uvicorn, "run", run)
    __main__.main()
    assert run.call_args.kwargs["port"] == 8502
    assert run.call_args.args[0] == "vikunja_webhook_listener.app:app"


def test_main_warns_when_directions_disabled(set_env, monkeypatch):
    # Both secrets unset — main() should still start (endpoints just return 401 at runtime).
    set_env(clear_keys=["GITHUB_WEBHOOK_SECRET", "VIKUNJA_WEBHOOK_SECRET"])
    from vikunja_webhook_listener import __main__

    monkeypatch.setattr(__main__.uvicorn, "run", MagicMock())
    __main__.main()  # must not raise
