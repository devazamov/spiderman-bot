import json
import logging
import random
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile

from bot import database as db
from bot.config import CATEGORIES
from bot.keyboards import main_menu_kb, content_list_kb, back_kb, content_actions_kb
from bot.ui import send_menu

router = Router()
log = logging.getLogger(__name__)

WELCOME_TEXT = (
    "🕸 <b>Assalomu alaykum, Peter!</b>\n\n"
    "Bu — Spider-Man olamiga bag'ishlangan bot.\n"
    "Filmlar, seriallar, multfilmlar, stikerlar, emojilar va videolarni shu yerdan toping.\n\n"
    "Kategoriyani tanlang yoki pastdagi Web-App orqali chiroyli interfeysda ko'ring 👇"
)


async def _maybe_send_sticker(message: Message):
    """Har safar bosh menyu/bo'limga kirganda, admin qo'shgan stikerlardan
    tasodifiy birini yuborib turadi — har safar boshqacha, qiziqarli bo'lishi uchun."""
    sticker_id = await db.get_random_sticker()
    if sticker_id:
        try:
            await message.answer_sticker(sticker_id)
        except Exception:
            pass


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.upsert_user(message.from_user.id, message.from_user.username)
    await _maybe_send_sticker(message)
    await send_menu(message, WELCOME_TEXT, main_menu_kb(), menu_key="main")


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await send_menu(callback, WELCOME_TEXT, main_menu_kb(), menu_key="main")
    await callback.answer()


@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    # SubscriptionMiddleware allaqachon obunani tekshiradi;
    # bu yerga yetib kelgan bo'lsa demak obuna bor.
    await callback.answer("✅ Obuna tasdiqlandi!")
    await send_menu(callback, WELCOME_TEXT, main_menu_kb(), menu_key="main")


@router.callback_query(F.data.startswith("cat:"))
async def show_category(callback: CallbackQuery):
    category = callback.data.split(":", 1)[1]
    items = await db.get_content_by_category(category)
    meta = CATEGORIES.get(category, {"title": category, "emoji": "🕷"})

    await _maybe_send_sticker(callback.message)

    if not items:
        await send_menu(
            callback,
            f"{meta['emoji']} <b>{meta['title']}</b>\n\n"
            "Hozircha bu bo'limda kontent yo'q. Tez orada qo'shiladi 🕸",
            back_kb(),
            menu_key=category,
        )
        await callback.answer()
        return

    await send_menu(
        callback,
        f"{meta['emoji']} <b>{meta['title']}</b>\n\nKerakli narsani tanlang:",
        content_list_kb(items, category),
        menu_key=category,
    )
    await callback.answer()


@router.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery):
    items = await db.list_favorites(callback.from_user.id)
    if not items:
        await send_menu(
            callback,
            "⭐ <b>Sevimlilar</b>\n\n"
            "Hozircha hech narsa saqlamagansiz.\n"
            "Istalgan kontentni ochib, ostidagi ⭐ tugmasini bosing — shu yerda paydo bo'ladi.",
            back_kb(),
            menu_key="favorites",
        )
    else:
        await send_menu(
            callback,
            f"⭐ <b>Sevimlilar</b> ({len(items)} ta)\n\nTanlang:",
            content_list_kb(items, "favorites"),
            menu_key="favorites",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("item:"))
async def send_item(callback: CallbackQuery):
    content_id = int(callback.data.split(":", 1)[1])
    item = await db.get_content_by_id(content_id)
    if not item:
        await callback.answer("Topilmadi 😕", show_alert=True)
        return

    await _send_content(callback.message, item, callback.from_user.id)
    await callback.answer("🕸 Yuborildi!")


@router.callback_query(F.data.startswith("favtoggle:"))
async def toggle_favorite(callback: CallbackQuery):
    content_id = int(callback.data.split(":", 1)[1])
    user_id = callback.from_user.id
    if await db.is_favorite(user_id, content_id):
        await db.remove_favorite(user_id, content_id)
        is_fav, toast = False, "💔 Sevimlilardan olib tashlandi"
    else:
        await db.add_favorite(user_id, content_id)
        is_fav, toast = True, "⭐ Sevimlilarga qo'shildi!"
    try:
        await callback.message.edit_reply_markup(reply_markup=content_actions_kb(content_id, is_fav))
    except Exception:
        pass
    await callback.answer(toast)


async def _send_content(message: Message, item: dict, user_id: int):
    caption = f"🕷 <b>{item['title']}</b>"
    if item.get("description"):
        caption += f"\n\n{item['description']}"

    file_type = item["file_type"]
    file_id = item["file_id"]
    is_fav = await db.is_favorite(user_id, item["id"])
    kb = content_actions_kb(item["id"], is_fav)

    if file_type == "video":
        await message.answer_video(file_id, caption=caption, reply_markup=kb)
    elif file_type == "photo":
        await message.answer_photo(file_id, caption=caption, reply_markup=kb)
    elif file_type == "animation":
        await message.answer_animation(file_id, caption=caption, reply_markup=kb)
    elif file_type == "sticker":
        await message.answer_sticker(file_id)
    elif file_type == "voice":
        await message.answer_voice(file_id, caption=caption, reply_markup=kb)
    elif file_type == "audio":
        await message.answer_audio(file_id, caption=caption, reply_markup=kb)
    else:
        await message.answer_document(file_id, caption=caption, reply_markup=kb)


@router.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    """Mini App'dan tg.sendData() orqali kelgan so'rovlarni qayta ishlaydi."""
    try:
        payload = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, AttributeError):
        return

    action = payload.get("action")
    if action == "get_content":
        content_id = payload.get("id")
        item = await db.get_content_by_id(int(content_id))
        if item:
            await _send_content(message, item, message.from_user.id)
        else:
            await message.answer("Topilmadi 😕")


# ---------- Hazilli stiker javoblari ----------
# Admin panelidan qo'shilgan stikerlar shu yerda ishlatiladi (bitta umumiy to'plam,
# butun bot bo'ylab bir xil). Foydalanuvchi botga oddiy (tushunarsiz) xabar yozganda
# tasodifiy stiker + qisqa hazil bilan javob qaytaradi.

FUNNY_LINES = [
    "Thwip! 🕸 Buni tushunmadim, lekin baribir stiker olib qo'y 😄",
    "Hmm, o'rgimchak hissim bunday buyruqni sezmayapti 🕷",
    "Bosh menyuga qaytish uchun /start bos, hozircha mana stiker 🕸",
    "New York osmonida uchib yuribman, xabaringni keyin o'qiyman 🕷😅",
    "Peter hozir band, lekin stikerdan mahrum qilmayman!",
]


@router.message(F.text & ~F.text.startswith("/"))
async def playful_fallback(message: Message):
    """Boshqa hech qanday handler ushlamagan oddiy matnli xabarlarga ishlaydi."""
    sticker_id = await db.get_random_sticker()
    if not sticker_id:
        return  # admin hali stiker qo'shmagan bo'lsa, hech narsa qilmaymiz
    await message.answer_sticker(sticker_id)
    await message.answer(random.choice(FUNNY_LINES))
