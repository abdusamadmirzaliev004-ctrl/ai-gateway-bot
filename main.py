from __future__ import annotations
import asyncio
import logging
import os
import sys
import traceback

from aiohttp import web

# ---- Logging FIRST so any later import error gets captured -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)
log = logging.getLogger("main")


def _resolve_port() -> int:
    """Railway injects PORT. Render/Fly do too. Fall back to WEBAPP_PORT, then 8080."""
    raw = os.environ.get("PORT") or os.environ.get("WEBAPP_PORT") or "8080"
    try:
        return int(raw)
    except ValueError:
        log.warning("Invalid PORT/WEBAPP_PORT=%r, falling back to 8080", raw)
        return 8080


def _resolve_host() -> str:
    return os.environ.get("WEBAPP_HOST", "0.0.0.0")


# =============================================================================
# Healthcheck server — starts FIRST, before DB / Telegram / settings parsing.
# Railway hits /health within seconds; if we wait for init_db() or
# bot.get_me() we time out. So we bind the port immediately and do real
# init in a background task.
# =============================================================================

_STATE = {"ready": False, "error": None, "mode": "starting"}


async def _health(_req):
    body = {
        "ok": True,
        "ready": _STATE["ready"],
        "mode": _STATE["mode"],
    }
    if _STATE["error"]:
        body["error"] = _STATE["error"]
    return web.json_response(body)


async def _build_health_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", _health)
    app.router.add_get("/", _health)
    return app


async def _bot_lifecycle(app: web.Application) -> None:
    """Background task: parse settings, init DB, start polling or webhook."""
    try:
        # Imports deferred so a config crash still leaves /health responding.
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

        from config.settings import get_settings
        from database.db import init_db
        from bot.handlers import user as user_handlers
        from bot.handlers import admin as admin_handlers

        log.info("Loading settings…")
        s = get_settings()
        log.info("Settings loaded. webhook=%s default_provider=%s",
                 bool(s.webhook_url), s.default_provider)

        log.info("Initializing database…")
        await init_db()
        log.info("Database ready.")

        bot = Bot(s.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        dp.include_router(admin_handlers.router)
        dp.include_router(user_handlers.router)

        # Sanity-check token early — surfaces "Unauthorized" cleanly in logs.
        try:
            me = await bot.get_me()
            log.info("Bot authorized as @%s (id=%s)", me.username, me.id)
        except Exception as e:
            log.error("Telegram getMe failed: %s", e)
            raise

        if s.webhook_url:
            url = s.webhook_url.rstrip("/") + s.webhook_path
            await bot.set_webhook(
                url=url,
                secret_token=s.webhook_secret or None,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"],
            )
            log.info("Webhook set: %s", url)
            SimpleRequestHandler(
                dispatcher=dp, bot=bot,
                secret_token=s.webhook_secret or None,
            ).register(app, path=s.webhook_path)
            setup_application(app, dp, bot=bot)
            _STATE["mode"] = "webhook"
            _STATE["ready"] = True
            log.info("Webhook handler registered. Bot ready.")
            # webhook mode: aiohttp server already running; nothing to await.
            return

        # Polling mode: aiohttp server keeps /health alive in parallel.
        await bot.delete_webhook(drop_pending_updates=True)
        _STATE["mode"] = "polling"
        _STATE["ready"] = True
        log.info("Starting long polling…")
        try:
            await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
        finally:
            await bot.session.close()

    except Exception as e:
        tb = traceback.format_exc()
        log.error("Bot lifecycle crashed:\n%s", tb)
        _STATE["error"] = f"{type(e).__name__}: {e}"
        _STATE["ready"] = False
        # Do NOT exit — keep /health responding so the operator can curl it
        # and see the error in the JSON body, instead of Railway just looping.


async def _on_startup(app: web.Application) -> None:
    # Spawn lifecycle in background; do NOT await it here — aiohttp must
    # finish startup so the TCP listener accepts the healthcheck.
    app["bot_task"] = asyncio.create_task(_bot_lifecycle(app))


async def _on_cleanup(app: web.Application) -> None:
    task = app.get("bot_task")
    if task:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


def _diagnose_env() -> None:
    """Print the env vars that determine deployment behavior so the operator
    can see at a glance what Railway actually injected."""
    def _mask(v: str) -> str:
        if not v:
            return "NOT SET"
        if len(v) <= 8:
            return "***"
        return f"{v[:4]}…{v[-4:]} (len={len(v)})"

    log.info("=== Environment diagnostic ===")
    log.info("WEBHOOK_URL=%s", os.environ.get("WEBHOOK_URL", "NOT SET"))
    log.info("PORT=%s", os.environ.get("PORT", "NOT SET"))
    log.info("WEBAPP_PORT=%s", os.environ.get("WEBAPP_PORT", "NOT SET"))
    log.info("BOT_TOKEN=%s", _mask(os.environ.get("BOT_TOKEN", "")))
    db = os.environ.get("DATABASE_URL", "NOT SET")
    if db != "NOT SET" and "@" in db:
        # Hide credentials, show host only
        host = db.split("@")[-1]
        log.info("DATABASE_URL=***@%s", host)
    else:
        log.info("DATABASE_URL=%s", db)
    log.info("DEFAULT_PROVIDER=%s", os.environ.get("DEFAULT_PROVIDER", "NOT SET"))
    log.info("ADMIN_IDS=%s", os.environ.get("ADMIN_IDS", "NOT SET"))
    log.info("RAILWAY_ENVIRONMENT=%s", os.environ.get("RAILWAY_ENVIRONMENT", "NOT SET"))
    log.info("==============================")


def _validate_webhook_url() -> None:
    """If WEBHOOK_URL is set, sanity-check it: must be https and the host
    must resolve via DNS. Fail loudly with the exact URL on error."""
    import socket
    from urllib.parse import urlparse

    raw = os.environ.get("WEBHOOK_URL", "").strip()
    if not raw:
        log.info("WEBHOOK_URL not set → bot will run in long-polling mode "
                 "(this works fine on Railway).")
        return

    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise RuntimeError(
            f"WEBHOOK_URL must start with https:// — got {raw!r}"
        )
    if not parsed.hostname:
        raise RuntimeError(f"WEBHOOK_URL has no hostname: {raw!r}")
    if parsed.scheme == "http":
        log.warning("WEBHOOK_URL uses http (Telegram requires https in prod): %s", raw)

    try:
        socket.gethostbyname(parsed.hostname)
        log.info("WEBHOOK_URL DNS OK: %s → %s",
                 parsed.hostname, socket.gethostbyname(parsed.hostname))
    except socket.gaierror as e:
        raise RuntimeError(
            f"WEBHOOK_URL hostname does not resolve via DNS. "
            f"URL={raw!r} hostname={parsed.hostname!r} error={e}. "
            f"On Railway, set WEBHOOK_URL to the public domain you generated "
            f"under Settings → Networking (e.g. https://your-app.up.railway.app)."
        ) from e


def main() -> None:
    _diagnose_env()
    _validate_webhook_url()
    host = _resolve_host()
    port = _resolve_port()
    log.info("Booting AI Gateway. Binding %s:%s", host, port)

    async def _factory():
        app = await _build_health_app()
        app.on_startup.append(_on_startup)
        app.on_cleanup.append(_on_cleanup)
        return app

    try:
        web.run_app(_factory(), host=host, port=port, print=None)
    except Exception:
        log.error("Fatal: web.run_app crashed:\n%s", traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
