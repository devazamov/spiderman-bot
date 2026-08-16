import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from bot.config import BOT_TOKEN, PORT, CATEGORIES, ADMIN_IDS
from bot import database as db
from bot.middlewares import SubscriptionMiddleware
from bot.handlers import user as user_handlers
from bot.handlers import admin as admin_handlers

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("spiderman_bot")

WEBAPP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp")


# ---------------- aiohttp API (Mini App uchun) ----------------

async def api_categories(request: web.Request):
    counts = await db.count_by_category()
    data = [
        {"key": k, "title": v["title"], "emoji": v["emoji"], "count": counts.get(k, 0)}
        for k, v in CATEGORIES.items()
    ]
    return web.json_response(data)


async def api_content(request: web.Request):
    category = request.query.get("category", "")
    if category not in CATEGORIES:
        return web.json_response({"error": "invalid category"}, status=400)
    items = await db.get_content_by_category(category)
    safe_items = [
        {"id": i["id"], "title": i["title"], "file_type": i["file_type"], "description": i.get("description", "")}
        for i in items
    ]
    return web.json_response(safe_items)


def build_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/categories", api_categories)
    app.router.add_get("/api/content", api_content)
    app.router.add_static("/", WEBAPP_DIR, show_index=True)
    return app


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN sozlanmagan! .env faylini tekshiring.")

    await db.init_db()
    await db.seed_admins(ADMIN_IDS)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    web_app = build_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"Web-server {PORT}-portda ishga tushdi (Mini App + API)")

    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Bot polling boshlandi 🕸")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
