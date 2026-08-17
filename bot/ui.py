from aiogram.types import Message, CallbackQuery
from bot import database as db


async def send_menu(event, text: str, keyboard=None, menu_key: str = None):
    """
    Menyuni chiqaradi. Agar shu menu_key uchun banner rasm o'rnatilgan bo'lsa,
    rasm + caption + tugmalar ko'rinishida; aks holda oddiy matn ko'rinishida yuboradi.
    `event` — Message yoki CallbackQuery bo'lishi mumkin.
    """
    banner = await db.get_banner(menu_key) if menu_key else None

    if isinstance(event, CallbackQuery):
        bot = event.message.bot
        chat_id = event.message.chat.id
        try:
            await event.message.delete()
        except Exception:
            pass
    else:
        bot = event.bot
        chat_id = event.chat.id

    if banner:
        if banner["file_type"] == "video":
            await bot.send_video(chat_id, banner["file_id"], caption=text, reply_markup=keyboard)
        else:
            await bot.send_photo(chat_id, banner["file_id"], caption=text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)
