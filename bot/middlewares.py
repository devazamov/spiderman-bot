from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot import database as db
from bot.config import CHANNEL_USERNAME


def _subscribe_kb(missing: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"📢 {u}", url=f"https://t.me/{u.lstrip('@')}")]
        for u in missing
    ]
    rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if await db.get_admin_role(user.id):
            return await handler(event, data)

        channels = await db.list_channels()
        usernames = [c["username"] for c in channels]
        if not usernames and CHANNEL_USERNAME:
            usernames = [CHANNEL_USERNAME]

        if not usernames:
            return await handler(event, data)

        bot = data["bot"]
        missing = []
        for uname in usernames:
            try:
                member = await bot.get_chat_member(chat_id=uname, user_id=user.id)
                if member.status in ("left", "kicked"):
                    missing.append(uname)
            except Exception:
                pass  # kanal tekshiruvi ishlamasa, o'sha kanalni bloklovchi qilmaymiz

        if not missing:
            return await handler(event, data)

        text = "🕸 Botdan foydalanish uchun avval quyidagi kanal(lar)ga a'zo bo'ling!"
        kb = _subscribe_kb(missing)
        if isinstance(event, Message):
            await event.answer(text, reply_markup=kb)
        elif isinstance(event, CallbackQuery):
            await event.answer("Avval kanal(lar)ga a'zo bo'ling!", show_alert=True)
            await event.message.answer(text, reply_markup=kb)
        return None
