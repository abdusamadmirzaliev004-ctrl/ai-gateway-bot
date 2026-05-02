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


def main() -> None:
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
