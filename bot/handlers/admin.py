import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot import database as db
from bot.config import CATEGORIES
from bot.keyboards import (
    admin_menu_kb, admin_category_kb, banner_menu_kb,
    admins_list_kb, role_choice_kb, channels_list_kb,
    stickers_menu_kb, stickers_list_kb,
)

router = Router()
log = logging.getLogger(__name__)


async def get_role(user_id: int):
    return await db.get_admin_role(user_id)


async def deny(callback: CallbackQuery):
    await callback.answer("Sizda bu amal uchun ruxsat yo'q ❌", show_alert=True)


class AddContent(StatesGroup):
    choosing_category = State()
    waiting_file = State()
    waiting_title = State()
    waiting_description = State()


class EditContent(StatesGroup):
    waiting_id = State()
    waiting_title = State()
    waiting_description = State()


class DeleteContent(StatesGroup):
    waiting_id = State()


class Broadcast(StatesGroup):
    waiting_message = State()


class SetBanner(StatesGroup):
    waiting_photo = State()


class AddSticker(StatesGroup):
    waiting_sticker = State()
    waiting_name = State()


class AddAdminFSM(StatesGroup):
    waiting_id = State()


class AddChannelFSM(StatesGroup):
    waiting_username = State()


@router.message(Command("admin"))
async def admin_panel(message: Message):
    role = await get_role(message.from_user.id)
    if not role:
        return
    await message.answer("🕸 <b>Admin panel</b>", reply_markup=admin_menu_kb(role == "super"))


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    await state.clear()
    await callback.message.edit_text("🕸 <b>Admin panel</b>", reply_markup=admin_menu_kb(role == "super"))
    await callback.answer()


@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    await state.clear()
    await callback.message.edit_text("🕸 <b>Admin panel</b>", reply_markup=admin_menu_kb(role == "super"))
    await callback.answer("Bekor qilindi")


# ---------- Kontent qo'shish ----------

@router.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    await state.set_state(AddContent.choosing_category)
    await callback.message.edit_text(
        "Qaysi kategoriyaga qo'shmoqchisiz?", reply_markup=admin_category_kb("addcat")
    )
    await callback.answer()


@router.callback_query(AddContent.choosing_category, F.data.startswith("addcat:"))
async def admin_add_category_chosen(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await state.set_state(AddContent.waiting_file)
    meta = CATEGORIES[category]
    await callback.message.edit_text(
        f"{meta['emoji']} <b>{meta['title']}</b>\n\n"
        "Endi kontentni yuboring: video, rasm, GIF, stiker, audio yoki fayl ko'rinishida."
    )
    await callback.answer()


@router.message(AddContent.waiting_file)
async def admin_add_file_received(message: Message, state: FSMContext):
    file_id = None
    file_type = None
    thumb_file_id = None

    if message.video:
        file_id, file_type = message.video.file_id, "video"
        if message.video.thumbnail:
            thumb_file_id = message.video.thumbnail.file_id
    elif message.photo:
        file_id, file_type = message.photo[-1].file_id, "photo"
    elif message.animation:
        file_id, file_type = message.animation.file_id, "animation"
        if message.animation.thumbnail:
            thumb_file_id = message.animation.thumbnail.file_id
    elif message.sticker:
        file_id, file_type = message.sticker.file_id, "sticker"
    elif message.voice:
        file_id, file_type = message.voice.file_id, "voice"
    elif message.audio:
        file_id, file_type = message.audio.file_id, "audio"
    elif message.document:
        file_id, file_type = message.document.file_id, "document"
        if message.document.thumbnail:
            thumb_file_id = message.document.thumbnail.file_id

    if not file_id:
        await message.answer("Iltimos, media fayl yuboring (video/rasm/gif/stiker/audio/fayl).")
        return

    await state.update_data(file_id=file_id, file_type=file_type, thumb_file_id=thumb_file_id)

    if file_type == "sticker":
        data = await state.get_data()
        content_id = await db.add_content(
            category=data["category"], title="Stiker", file_id=file_id, file_type=file_type,
        )
        await state.clear()
        role = await get_role(message.from_user.id)
        await message.answer(f"✅ Qo'shildi! (ID: {content_id})", reply_markup=admin_menu_kb(role == "super"))
        return

    await state.set_state(AddContent.waiting_title)
    await message.answer("Sarlavha (nomi)ni kiriting:")


@router.message(AddContent.waiting_title)
async def admin_add_title_received(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddContent.waiting_description)
    await message.answer("Qisqacha tavsif kiriting (bo'lmasa \"-\" deb yozing):")


@router.message(AddContent.waiting_description)
async def admin_add_description_received(message: Message, state: FSMContext):
    data = await state.get_data()
    description = "" if message.text.strip() == "-" else message.text

    content_id = await db.add_content(
        category=data["category"], title=data["title"], file_id=data["file_id"],
        file_type=data["file_type"], description=description, thumb_file_id=data.get("thumb_file_id"),
    )
    await state.clear()
    meta = CATEGORIES[data["category"]]
    role = await get_role(message.from_user.id)
    await message.answer(
        f"✅ <b>{data['title']}</b> {meta['title']} bo'limiga qo'shildi! (ID: {content_id})",
        reply_markup=admin_menu_kb(role == "super"),
    )


# ---------- Kontent tahrirlash ----------

@router.callback_query(F.data == "admin_edit")
async def admin_edit_start(callback: CallbackQuery, state: FSMContext):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    await state.set_state(EditContent.waiting_id)
    await callback.message.edit_text("Tahrirlamoqchi bo'lgan kontentning ID raqamini yuboring.")
    await callback.answer()


@router.message(EditContent.waiting_id)
async def admin_edit_id_received(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqam (ID) yuboring.")
        return
    content_id = int(message.text.strip())
    item = await db.get_content_by_id(content_id)
    if not item:
        await message.answer("Bunday ID topilmadi.")
        await state.clear()
        return
    await state.update_data(content_id=content_id)
    await state.set_state(EditContent.waiting_title)
    await message.answer(
        f"Hozirgi nom: <b>{item['title']}</b>\n\n"
        "Yangi nomni yuboring (o'zgartirmaslik uchun \"-\" yuboring):"
    )


@router.message(EditContent.waiting_title)
async def admin_edit_title_received(message: Message, state: FSMContext):
    title = None if message.text.strip() == "-" else message.text
    await state.update_data(title=title)
    await state.set_state(EditContent.waiting_description)
    await message.answer("Yangi tavsifni yuboring (o'zgartirmaslik uchun \"-\"):")


@router.message(EditContent.waiting_description)
async def admin_edit_description_received(message: Message, state: FSMContext):
    data = await state.get_data()
    description = None if message.text.strip() == "-" else message.text
    await db.update_content(data["content_id"], title=data.get("title"), description=description)
    await state.clear()
    role = await get_role(message.from_user.id)
    await message.answer("✅ Kontent yangilandi!", reply_markup=admin_menu_kb(role == "super"))


# ---------- Kontent ro'yxati ----------

@router.callback_query(F.data == "admin_list")
async def admin_list_start(callback: CallbackQuery):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    await callback.message.edit_text("Qaysi bo'limni ko'rsataman?", reply_markup=admin_category_kb("listcat"))
    await callback.answer()


@router.callback_query(F.data.startswith("listcat:"))
async def admin_list_category(callback: CallbackQuery):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    category = callback.data.split(":", 1)[1]
    items = await db.get_content_by_category(category)
    meta = CATEGORIES[category]

    if not items:
        text = f"{meta['emoji']} <b>{meta['title']}</b>\n\nBo'sh."
    else:
        lines = [f"{meta['emoji']} <b>{meta['title']}</b> ({len(items)} ta)\n"]
        for it in items[:50]:
            lines.append(f"#{it['id']} — {it['title']}")
        if len(items) > 50:
            lines.append(f"\n... va yana {len(items) - 50} ta")
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=admin_menu_kb(role == "super"))
    await callback.answer()


# ---------- Kontent o'chirish ----------

@router.callback_query(F.data == "admin_delete")
async def admin_delete_start(callback: CallbackQuery, state: FSMContext):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    await state.set_state(DeleteContent.waiting_id)
    await callback.message.edit_text(
        "O'chirmoqchi bo'lgan kontentning ID raqamini yuboring.\n"
        "(ID ni Kontent ro'yxati bo'limidan ko'rishingiz mumkin)"
    )
    await callback.answer()


@router.message(DeleteContent.waiting_id)
async def admin_delete_id_received(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqam yuboring.")
        return
    content_id = int(message.text.strip())
    item = await db.get_content_by_id(content_id)
    if not item:
        await message.answer("Bunday ID topilmadi.")
        await state.clear()
        return
    await db.delete_content(content_id)
    await state.clear()
    role = await get_role(message.from_user.id)
    await message.answer(f"🗑 O'chirildi: {item['title']}", reply_markup=admin_menu_kb(role == "super"))


# ---------- Statistika ----------

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    counts = await db.count_by_category()
    total_users = await db.count_users()
    lines = ["📊 <b>Statistika</b>\n"]
    for key, meta in CATEGORIES.items():
        lines.append(f"{meta['emoji']} {meta['title']}: {counts.get(key, 0)}")
    lines.append(f"\n👥 Foydalanuvchilar: {total_users}")
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb(role == "super"))
    await callback.answer()


# ---------- Menyu rasmlari (banner) ----------

@router.callback_query(F.data == "admin_banners")
async def admin_banners_start(callback: CallbackQuery):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    await callback.message.edit_text(
        "🖼 Qaysi menyu tepasida rasm ko'rinsin?\n\n"
        "Eslatma: rasmni o'zingiz yuklaysiz (fan-art yoki foydalanish huquqingiz bor rasm).",
        reply_markup=banner_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bannerkey:"))
async def admin_banner_key_chosen(callback: CallbackQuery, state: FSMContext):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    menu_key = callback.data.split(":", 1)[1]
    await state.update_data(menu_key=menu_key)
    await state.set_state(SetBanner.waiting_photo)
    await callback.message.edit_text(
        "Shu menyu tepasida ko'rinadigan rasm YOKI videoni yuboring.\n"
        "(Mavjudini o'chirish uchun \"o'chir\" deb yozing)"
    )
    await callback.answer()


@router.message(SetBanner.waiting_photo)
async def admin_banner_photo_received(message: Message, state: FSMContext):
    data = await state.get_data()
    menu_key = data["menu_key"]
    role = await get_role(message.from_user.id)

    if message.text and message.text.strip().lower() in ("o'chir", "ochir", "-"):
        await db.remove_banner(menu_key)
        await state.clear()
        await message.answer("🗑 O'chirildi.", reply_markup=admin_menu_kb(role == "super"))
        return

    if message.video:
        file_id, file_type = message.video.file_id, "video"
    elif message.photo:
        file_id, file_type = message.photo[-1].file_id, "photo"
    else:
        await message.answer("Iltimos, rasm yoki video yuboring, yoki o'chirish uchun \"o'chir\" deb yozing.")
        return

    await db.set_banner(menu_key, file_id, file_type)
    await state.clear()
    label = "Video" if file_type == "video" else "Rasm"
    await message.answer(f"✅ {label} o'rnatildi!", reply_markup=admin_menu_kb(role == "super"))


# ---------- Stikerlar (hazilli auto-javob to'plami) ----------

@router.callback_query(F.data == "admin_stickers")
async def admin_stickers_menu(callback: CallbackQuery):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    count = await db.count_stickers()
    await callback.message.edit_text(
        "🎭 <b>Stikerlar</b>\n\n"
        "Bu yerga qo'shgan stikerlaringiz botning turli joylarida "
        "(bosh menyu, bo'limlarga kirganda, tushunarsiz xabarlarga javoban) "
        "tasodifiy tarzda chiqib turadi — butun bot bo'ylab bitta umumiy to'plam.",
        reply_markup=stickers_menu_kb(count),
    )
    await callback.answer()


@router.callback_query(F.data == "stickers_add")
async def admin_sticker_add_start(callback: CallbackQuery, state: FSMContext):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    await state.set_state(AddSticker.waiting_sticker)
    await callback.message.edit_text("Stikerni menga yuboring (Telegram stiker ko'rinishida):")
    await callback.answer()


@router.message(AddSticker.waiting_sticker)
async def admin_sticker_add_received(message: Message, state: FSMContext):
    if not message.sticker:
        await message.answer("Iltimos, aynan stiker (sticker) yuboring.")
        return
    await state.update_data(file_id=message.sticker.file_id)
    await state.set_state(AddSticker.waiting_name)
    await message.answer(
        "Endi shu stiker uchun qisqa nom yozing (masalan: <i>kulgili</i>, <i>salom</i>, <i>tabriklov</i>).\n"
        "Bu nom faqat siz — adminlar uchun, ro'yxatda ko'rinadi."
    )


@router.message(AddSticker.waiting_name)
async def admin_sticker_name_received(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Iltimos, nom uchun matn yuboring.")
        return
    data = await state.get_data()
    sticker_id = await db.add_sticker(data["file_id"], message.from_user.id, message.text.strip())
    await state.clear()
    count = await db.count_stickers()
    await message.answer(
        f"✅ Stiker qo'shildi! (\"{message.text.strip()}\", jami: {count} ta)",
        reply_markup=stickers_menu_kb(count),
    )


@router.callback_query(F.data == "stickers_list")
async def admin_stickers_list(callback: CallbackQuery):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    stickers = await db.list_stickers()
    if not stickers:
        await callback.message.edit_text(
            "🎭 Hozircha stiker yo'q.", reply_markup=stickers_menu_kb(0)
        )
    else:
        await callback.message.edit_text(
            f"🎭 <b>Stikerlar</b> ({len(stickers)} ta)\n\nO'chirish uchun bosing:",
            reply_markup=stickers_list_kb(stickers),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("sticker_rm:"))
async def admin_sticker_remove(callback: CallbackQuery):
    role = await get_role(callback.from_user.id)
    if not role:
        return await deny(callback)
    sticker_id = int(callback.data.split(":", 1)[1])
    await db.delete_sticker(sticker_id)
    stickers = await db.list_stickers()
    await callback.message.edit_text(
        f"🎭 <b>Stikerlar</b> ({len(stickers)} ta)\n\nO'chirish uchun bosing:",
        reply_markup=stickers_list_kb(stickers) if stickers else stickers_menu_kb(0),
    )
    await callback.answer("O'chirildi")


# ---------- Adminlar (faqat super) ----------

@router.callback_query(F.data == "admin_admins")
async def admin_admins_list(callback: CallbackQuery):
    if await get_role(callback.from_user.id) != "super":
        return await deny(callback)
    admins = await db.list_admins()
    await callback.message.edit_text(
        "👤 <b>Adminlar</b>\n👑 super admin — hammasi mumkin\n🛡 moderator — kontent bilan ishlaydi\n\n"
        "O'chirish uchun ro'yxatdan bosing:",
        reply_markup=admins_list_kb(admins),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_admin")
async def admin_add_admin_start(callback: CallbackQuery, state: FSMContext):
    if await get_role(callback.from_user.id) != "super":
        return await deny(callback)
    await state.set_state(AddAdminFSM.waiting_id)
    await callback.message.edit_text(
        "Yangi admin qilmoqchi bo'lgan foydalanuvchining Telegram user ID sini yuboring.\n"
        "(ID ni bilish uchun o'sha odam @userinfobot ga /start bossin)"
    )
    await callback.answer()


@router.message(AddAdminFSM.waiting_id)
async def admin_add_admin_id_received(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqam (user ID) yuboring.")
        return
    await state.update_data(new_admin_id=int(message.text.strip()))
    await message.answer("Qaysi darajada admin bo'lsin?", reply_markup=role_choice_kb())


@router.callback_query(F.data.startswith("role:"))
async def admin_role_chosen(callback: CallbackQuery, state: FSMContext):
    if await get_role(callback.from_user.id) != "super":
        return await deny(callback)
    data = await state.get_data()
    new_admin_id = data.get("new_admin_id")
    if not new_admin_id:
        await callback.answer()
        return
    role = callback.data.split(":", 1)[1]
    await db.add_admin(new_admin_id, role, callback.from_user.id)
    await state.clear()
    admins = await db.list_admins()
    label = "👑 Super admin" if role == "super" else "🛡 Moderator"
    await callback.message.edit_text(
        f"✅ {new_admin_id} — {label} qilib qo'shildi.", reply_markup=admins_list_kb(admins)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_rm:"))
async def admin_remove(callback: CallbackQuery):
    if await get_role(callback.from_user.id) != "super":
        return await deny(callback)
    target_id = int(callback.data.split(":", 1)[1])
    target_role = await db.get_admin_role(target_id)
    if target_role == "super" and await db.count_super_admins() <= 1:
        await callback.answer("Oxirgi super adminni o'chirib bo'lmaydi!", show_alert=True)
        return
    await db.remove_admin(target_id)
    admins = await db.list_admins()
    await callback.message.edit_text("👤 <b>Adminlar</b>", reply_markup=admins_list_kb(admins))
    await callback.answer("O'chirildi")


# ---------- Majburiy obuna kanallari (faqat super) ----------

@router.callback_query(F.data == "admin_channels")
async def admin_channels_list(callback: CallbackQuery):
    if await get_role(callback.from_user.id) != "super":
        return await deny(callback)
    channels = await db.list_channels()
    await callback.message.edit_text(
        "📢 <b>Majburiy obuna kanallari</b>\n\nFoydalanuvchilar shu kanal(lar)ga a'zo bo'lmasa botdan foydalana olmaydi.",
        reply_markup=channels_list_kb(channels),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_channel")
async def admin_add_channel_start(callback: CallbackQuery, state: FSMContext):
    if await get_role(callback.from_user.id) != "super":
        return await deny(callback)
    await state.set_state(AddChannelFSM.waiting_username)
    await callback.message.edit_text(
        "Kanal usernameni yuboring (masalan @mening_kanalim).\n\n"
        "⚠️ Bot o'sha kanalda ADMIN bo'lishi shart, aks holda obuna tekshiruvi ishlamaydi."
    )
    await callback.answer()


@router.message(AddChannelFSM.waiting_username)
async def admin_add_channel_received(message: Message, state: FSMContext):
    username = message.text.strip()
    if not username.startswith("@"):
        await message.answer("Username @ bilan boshlanishi kerak, masalan @kanalim. Qayta yuboring:")
        return
    await db.add_channel(username)
    await state.clear()
    channels = await db.list_channels()
    await message.answer("✅ Kanal qo'shildi!", reply_markup=channels_list_kb(channels))


@router.callback_query(F.data.startswith("chan_rm:"))
async def admin_channel_remove(callback: CallbackQuery):
    if await get_role(callback.from_user.id) != "super":
        return await deny(callback)
    chan_id = int(callback.data.split(":", 1)[1])
    await db.remove_channel(chan_id)
    channels = await db.list_channels()
    await callback.message.edit_text("📢 <b>Majburiy obuna kanallari</b>", reply_markup=channels_list_kb(channels))
    await callback.answer("O'chirildi")


# ---------- Broadcast (faqat super) ----------

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if await get_role(callback.from_user.id) != "super":
        return await deny(callback)
    await state.set_state(Broadcast.waiting_message)
    await callback.message.edit_text("Barcha foydalanuvchilarga yuboriladigan xabarni yozing:")
    await callback.answer()


@router.message(Broadcast.waiting_message)
async def admin_broadcast_send(message: Message, state: FSMContext):
    await state.clear()
    user_ids = await db.get_all_user_ids()
    sent, failed = 0, 0
    status = await message.answer(f"Yuborilmoqda... 0/{len(user_ids)}")

    for i, uid in enumerate(user_ids, start=1):
        try:
            await message.bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
        except Exception:
            failed += 1
        if i % 20 == 0:
            await status.edit_text(f"Yuborilmoqda... {i}/{len(user_ids)}")
        await asyncio.sleep(0.05)

    role = await get_role(message.from_user.id)
    await status.edit_text(
        f"✅ Yuborildi: {sent} ta\n❌ Xatolik: {failed} ta", reply_markup=admin_menu_kb(role == "super")
    )
