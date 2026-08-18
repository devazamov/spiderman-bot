from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from bot.config import CATEGORIES, CHANNEL_USERNAME, WEBAPP_URL


def main_menu_kb() -> InlineKeyboardMarkup:
    rows = []
    cats = list(CATEGORIES.items())
    for i in range(0, len(cats), 2):
        row = []
        for key, meta in cats[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    text=f"{meta['emoji']} {meta['title']}",
                    callback_data=f"cat:{key}",
                )
            )
        rows.append(row)

    if WEBAPP_URL:
        rows.append([
            InlineKeyboardButton(
                text="🕸 Web-App'ni ochish",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ])

    rows.append([InlineKeyboardButton(text="⭐ Sevimlilar", callback_data="favorites")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscribe_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga o'tish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")],
        ]
    )


def content_list_kb(items: list, category: str) -> InlineKeyboardMarkup:
    rows = []
    for item in items[:30]:
        rows.append([
            InlineKeyboardButton(text=f"🕷 {item['title']}", callback_data=f"item:{item['id']}")
        ])
    rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="back_main")]]
    )


def content_actions_kb(content_id: int, is_fav: bool) -> InlineKeyboardMarkup:
    text = "💔 Sevimlilardan olib tashlash" if is_fav else "⭐ Sevimlilarga qo'shish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=f"favtoggle:{content_id}")]
    ])


def admin_menu_kb(is_super: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕ Kontent qo'shish", callback_data="admin_add")],
        [InlineKeyboardButton(text="✏️ Kontent tahrirlash", callback_data="admin_edit")],
        [InlineKeyboardButton(text="📋 Kontent ro'yxati", callback_data="admin_list")],
        [InlineKeyboardButton(text="🗑 Kontent o'chirish", callback_data="admin_delete")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🖼 Menyu rasmlari", callback_data="admin_banners")],
        [InlineKeyboardButton(text="🎭 Stikerlar", callback_data="admin_stickers")],
    ]
    if is_super:
        rows.append([InlineKeyboardButton(text="📣 Xabar yuborish (barchaga)", callback_data="admin_broadcast")])
        rows.append([InlineKeyboardButton(text="👤 Adminlar", callback_data="admin_admins")])
        rows.append([InlineKeyboardButton(text="📢 Kanallar", callback_data="admin_channels")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


BANNER_MENUS = [("main", "🏠 Asosiy menyu")] + [
    (k, f"{v['emoji']} {v['title']}") for k, v in CATEGORIES.items()
] + [("webapp_bg", "🎨 Mini App orqa foni (osilib turuvchi rasm)")]


def banner_menu_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=title, callback_data=f"bannerkey:{key}")] for key, title in BANNER_MENUS]
    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def stickers_menu_kb(count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📋 Ro'yxat ({count} ta)", callback_data="stickers_list")],
        [InlineKeyboardButton(text="➕ Stiker qo'shish", callback_data="stickers_add")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")],
    ])


def stickers_list_kb(stickers: list) -> InlineKeyboardMarkup:
    rows = []
    for s in stickers[:40]:
        label = f"❌ {s['name']}" if s.get("name") else f"❌ #{s['id']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"sticker_rm:{s['id']}")])
    rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_stickers")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admins_list_kb(admins: list) -> InlineKeyboardMarkup:
    rows = []
    for a in admins:
        label = f"{'👑' if a['role'] == 'super' else '🛡'} {a['user_id']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"admin_rm:{a['user_id']}")])
    rows.append([InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="admin_add_admin")])
    rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def role_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Super admin", callback_data="role:super")],
        [InlineKeyboardButton(text="🛡 Moderator", callback_data="role:moderator")],
    ])


def channels_list_kb(channels: list) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"❌ {c['username']}", callback_data=f"chan_rm:{c['id']}")] for c in channels]
    rows.append([InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin_add_channel")])
    rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_category_kb(prefix: str) -> InlineKeyboardMarkup:
    rows = []
    cats = list(CATEGORIES.items())
    for i in range(0, len(cats), 2):
        row = []
        for key, meta in cats[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    text=f"{meta['emoji']} {meta['title']}",
                    callback_data=f"{prefix}:{key}",
                )
            )
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
