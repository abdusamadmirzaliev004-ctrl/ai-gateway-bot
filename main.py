from __future__ import annotations
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config.settings import get_settings
from database.db import init_db
from bot.handlers import user as user_handlers
from bot.handlers import admin as admin_handlers


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("main")


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)
    return dp


async def on_startup(bot: Bot, settings) -> None:
    await init_db()
    if settings.use_webhook:
        url = settings.webhook_url.rstrip("/") + settings.webhook_path
        await bot.set_webhook(url=url, secret_token=settings.webhook_secret or None,
                              drop_pending_updates=True,
                              allowed_updates=["message", "callback_query"])
        log.info("Webhook set: %s", url)
    else:
        await bot.delete_webhook(drop_pending_updates=True)


async def on_shutdown(bot: Bot) -> None:
    await bot.session.close()


async def run_polling() -> None:
    s = get_settings()
    bot = Bot(s.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()
    await on_startup(bot, s)
    log.info("Starting polling…")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await on_shutdown(bot)


def run_webhook() -> None:
    s = get_settings()
    bot = Bot(s.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()

    app = web.Application()

    async def _startup(_app):
        await on_startup(bot, s)

    async def _shutdown(_app):
        await on_shutdown(bot)

    async def _health(_req):
        return web.json_response({"ok": True})

    app.router.add_get("/health", _health)
    app.on_startup.append(_startup)
    app.on_shutdown.append(_shutdown)

    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=s.webhook_secret or None) \
        .register(app, path=s.webhook_path)
    setup_application(app, dp, bot=bot)

    port = int(os.getenv("PORT", s.webapp_port))  # Railway/Render inject $PORT
    log.info("Starting webhook server on %s:%s%s", s.webapp_host, port, s.webhook_path)
    web.run_app(app, host=s.webapp_host, port=port)


def main() -> None:
    s = get_settings()
    if s.use_webhook:
        run_webhook()
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
