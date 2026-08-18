import asyncio
import hashlib
import io
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
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
    return web.json_response([_serialize_item(i) for i in items])


def _serialize_item(i: dict) -> dict:
    return {
        "id": i["id"],
        "title": i["title"],
        "file_type": i["file_type"],
        "description": i.get("description", ""),
        "views": i.get("views", 0),
        "has_thumb": bool(i.get("thumb_file_id")),
    }


async def api_search(request: web.Request):
    q = request.query.get("q", "").strip()
    if not q:
        return web.json_response([])
    items = await db.search_content(q)
    return web.json_response([_serialize_item(i) | {"category": i["category"]} for i in items])


async def api_top(request: web.Request):
    items = await db.get_top_viewed(12)
    return web.json_response([_serialize_item(i) | {"category": i["category"]} for i in items])


async def api_view(request: web.Request):
    content_id = int(request.match_info["id"])
    await db.increment_views(content_id)
    return web.json_response({"ok": True})


async def api_favorites(request: web.Request):
    try:
        user_id = int(request.query.get("user_id", "0"))
    except ValueError:
        return web.json_response([])
    if not user_id:
        return web.json_response([])
    items = await db.list_favorites(user_id)
    return web.json_response([_serialize_item(i) | {"category": i["category"]} for i in items])


async def api_favorite_toggle(request: web.Request):
    try:
        data = await request.json()
        user_id = int(data["user_id"])
        content_id = int(data["content_id"])
    except (ValueError, KeyError, TypeError):
        return web.json_response({"error": "bad request"}, status=400)

    if await db.is_favorite(user_id, content_id):
        await db.remove_favorite(user_id, content_id)
        is_fav = False
    else:
        await db.add_favorite(user_id, content_id)
        is_fav = True
    return web.json_response({"is_favorite": is_fav})


async def api_thumb(request: web.Request):
    """Video/animatsiya/fayl kontentining kichik old-ko'rish rasmini proksi qiladi."""
    content_id = int(request.match_info["id"])
    item = await db.get_content_by_id(content_id)
    if not item or not item.get("thumb_file_id"):
        raise web.HTTPNotFound()

    bot: Bot = request.app["bot"]
    tg_file = await bot.get_file(item["thumb_file_id"])
    buf = io.BytesIO()
    await bot.download_file(tg_file.file_path, destination=buf)
    buf.seek(0)
    return web.Response(body=buf.read(), content_type="image/jpeg",
                         headers={"Cache-Control": "public, max-age=600"})


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
    app.router.add_get("/api/search", api_search)
    app.router.add_get("/api/top", api_top)
    app.router.add_post("/api/view/{id}", api_view)
    app.router.add_get("/api/favorites", api_favorites)
    app.router.add_post("/api/favorite/toggle", api_favorite_toggle)
    app.router.add_get("/api/thumb/{id}", api_thumb)
    app.router.add_get("/api/banner/{key}", api_banner_image)

    # Telegram shu manzilga POST qilib xabarlarni yuboradi (webhook rejimi).
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # Mini App statik fayllari eng oxirida — u "catch-all" bo'lgani uchun.
    app.router.add_static("/", WEBAPP_DIR, show_index=True)
    return app


async def setup_bot_profile(bot: Bot):
    """Bot buyruqlari va tavsif matnlarini avtomatik o'rnatadi
    (BotFather'ga qo'lda kirmasdan — Bot API orqali)."""
    await bot.set_my_commands([
        BotCommand(command="start", description="🕸 Botni ishga tushirish / bosh menyu"),
        BotCommand(command="admin", description="🛠 Admin panel (faqat adminlar uchun)"),
    ])
    await bot.set_my_description(
        "🕸 Spider-Man olamiga bag'ishlangan bot!\n\n"
        "Filmlar, seriallar, multfilmlar, stikerlar, emojilar va videolarni shu yerdan toping. "
        "Sevimlilaringizni saqlang, qidiruv orqali izlang va Mini App'da chiroyli interfeysda ko'ring 🕷"
    )
    await bot.set_my_short_description(
        "Spider-Man filmlari, seriallari, stikerlari va videolari — bittasida 🕸"
    )
    log.info("Bot buyruqlari va tavsiflari o'rnatildi ✅")


async def keep_alive_pinger():
    """Render bepul tarifida servis 15 daqiqa faoliyatsizlikdan keyin
    'uxlab qoladi'. Buni oldini olish uchun bot o'zining ochiq URL'iga
    har 10 daqiqada bir marta so'rov yuborib, doim 'uyg'oq' turadi."""
    if not WEBAPP_URL:
        return
    await asyncio.sleep(30)  # server to'liq ishga tushguncha kutamiz
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(WEBAPP_URL, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    log.info(f"🔁 Keep-alive ping: {resp.status}")
            except Exception as e:
                log.warning(f"Keep-alive ping xatosi: {e}")
            await asyncio.sleep(600)  # 10 daqiqada bir


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN sozlanmagan! .env faylini tekshiring.")

    await db.init_db()
    await db.seed_admins(ADMIN_IDS)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    await setup_bot_profile(bot)

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

    asyncio.create_task(keep_alive_pinger())
    log.info("🔁 Keep-alive pinger ishga tushdi — bot endi uxlamaydi")

    # Jarayonni tirik ushlab turish (aiohttp server fon rejimida ishlayveradi)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
