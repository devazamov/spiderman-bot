import asyncio
import hashlib
import io
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import BOT_TOKEN, PORT, CATEGORIES, ADMIN_IDS, WEBAPP_URL
from bot import database as db
from bot.middlewares import SubscriptionMiddleware
from bot.handlers import user as user_handlers
from bot.handlers import admin as admin_handlers

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("spiderman_bot")

WEBAPP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp")

# Webhook manzilini bot tokenidan hosil qilingan hash bilan yashiramiz —
# shunday qilib faqat Telegram biladigan maxfiy yo'l bo'ladi.
WEBHOOK_PATH = "/webhook/" + hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]


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


async def api_banner_image(request: web.Request):
    """Admin bot orqali yuklagan banner rasmini Mini App uchun proksi qiladi.
    Faqat 'photo' turidagi bannerlar uchun ishlaydi (video Mini App'da ishlatilmaydi)."""
    menu_key = request.match_info.get("key", "main")
    banner = await db.get_banner(menu_key)
    if not banner or banner["file_type"] != "photo":
        raise web.HTTPNotFound()

    bot: Bot = request.app["bot"]
    tg_file = await bot.get_file(banner["file_id"])
    buf = io.BytesIO()
    await bot.download_file(tg_file.file_path, destination=buf)
    buf.seek(0)
    return web.Response(body=buf.read(), content_type="image/jpeg",
                         headers={"Cache-Control": "public, max-age=300"})


def build_web_app(bot: Bot, dp: Dispatcher) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/api/categories", api_categories)
    app.router.add_get("/api/content", api_content)
    app.router.add_get("/api/banner/{key}", api_banner_image)

    # Telegram shu manzilga POST qilib xabarlarni yuboradi (webhook rejimi).
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # Mini App statik fayllari eng oxirida — u "catch-all" bo'lgani uchun.
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

    web_app = build_web_app(bot, dp)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"Web-server {PORT}-portda ishga tushdi (Mini App + API)")

    if WEBAPP_URL:
        webhook_url = WEBAPP_URL.rstrip("/") + WEBHOOK_PATH
        await bot.set_webhook(
            webhook_url,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types(),
        )
        log.info(f"Webhook o'rnatildi: {webhook_url}")
        log.info("Bot webhook rejimida ishlamoqda 🕸 (Render uxlab qolsa, keyingi xabar uni uyg'otadi)")
    else:
        log.warning("WEBAPP_URL sozlanmagan — webhook o'rnatib bo'lmadi, bot xabar qabul qilmaydi!")

    # Jarayonni tirik ushlab turish (aiohttp server fon rejimida ishlayveradi)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
