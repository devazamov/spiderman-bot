import aiosqlite
from bot.config import DB_PATH

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    file_id TEXT NOT NULL,
    file_type TEXT NOT NULL,      -- video, photo, animation, sticker, document
    description TEXT,
    thumb_file_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ADMINS_SQL = """
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    role TEXT NOT NULL DEFAULT 'moderator',   -- 'super' | 'moderator'
    added_by INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CHANNELS_SQL = """
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,   -- masalan @mening_kanalim
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_BANNERS_SQL = """
CREATE TABLE IF NOT EXISTS banners (
    menu_key TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    file_type TEXT NOT NULL DEFAULT 'photo'
);
"""

CREATE_STICKERS_SQL = """
CREATE TABLE IF NOT EXISTS stickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    added_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.execute(CREATE_USERS_SQL)
        await db.execute(CREATE_ADMINS_SQL)
        await db.execute(CREATE_CHANNELS_SQL)
        await db.execute(CREATE_BANNERS_SQL)
        await db.execute(CREATE_STICKERS_SQL)

        # Eski bazalarda 'banners' jadvalida file_type ustuni bo'lmasligi mumkin — migratsiya
        cursor = await db.execute("PRAGMA table_info(banners)")
        cols = [row[1] for row in await cursor.fetchall()]
        if "file_type" not in cols:
            await db.execute("ALTER TABLE banners ADD COLUMN file_type TEXT NOT NULL DEFAULT 'photo'")

        await db.commit()


async def seed_admins(initial_ids: list):
    """Birinchi ishga tushirishda .env dagi ADMIN_IDS larni 'super' sifatida bazaga yozadi."""
    if not initial_ids:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM admins")
        row = await cursor.fetchone()
        if row[0] > 0:
            return  # allaqachon adminlar bor, qayta seed qilmaymiz
        for uid in initial_ids:
            await db.execute(
                "INSERT OR IGNORE INTO admins (user_id, role, added_by) VALUES (?, 'super', ?)",
                (uid, uid),
            )
        await db.commit()


async def add_content(category: str, title: str, file_id: str, file_type: str,
                       description: str = "", thumb_file_id: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO content (category, title, file_id, file_type, description, thumb_file_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (category, title, file_id, file_type, description, thumb_file_id),
        )
        await db.commit()
        return cursor.lastrowid


async def get_content_by_category(category: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM content WHERE category = ? ORDER BY created_at DESC", (category,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_content_by_id(content_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM content WHERE id = ?", (content_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_content(content_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM content WHERE id = ?", (content_id,))
        await db.commit()


async def count_by_category():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT category, COUNT(*) as cnt FROM content GROUP BY category"
        )
        rows = await cursor.fetchall()
        return {r["category"]: r["cnt"] for r in rows}


async def upsert_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username or ""),
        )
        await db.commit()


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def update_content(content_id: int, title: str = None, description: str = None):
    fields, values = [], []
    if title is not None:
        fields.append("title = ?")
        values.append(title)
    if description is not None:
        fields.append("description = ?")
        values.append(description)
    if not fields:
        return
    values.append(content_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE content SET {', '.join(fields)} WHERE id = ?", values)
        await db.commit()


# ---------------- Adminlar ----------------

async def get_admin_role(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT role FROM admins WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None


async def list_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM admins ORDER BY role, added_at")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_admin(user_id: int, role: str, added_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO admins (user_id, role, added_by) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET role = excluded.role",
            (user_id, role, added_by),
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()


async def count_super_admins() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM admins WHERE role = 'super'")
        row = await cursor.fetchone()
        return row[0] if row else 0


# ---------------- Majburiy obuna kanallari ----------------

async def add_channel(username: str):
    username = username if username.startswith("@") else f"@{username}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO channels (username) VALUES (?)", (username,))
        await db.commit()


async def remove_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        await db.commit()


async def list_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM channels ORDER BY added_at")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ---------------- Menyu rasmlari (banner: rasm yoki video) ----------------

async def set_banner(menu_key: str, file_id: str, file_type: str = "photo"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO banners (menu_key, file_id, file_type) VALUES (?, ?, ?) "
            "ON CONFLICT(menu_key) DO UPDATE SET file_id = excluded.file_id, file_type = excluded.file_type",
            (menu_key, file_id, file_type),
        )
        await db.commit()


async def get_banner(menu_key: str):
    """{'file_id': ..., 'file_type': 'photo'|'video'} yoki None qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT file_id, file_type FROM banners WHERE menu_key = ?", (menu_key,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def remove_banner(menu_key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM banners WHERE menu_key = ?", (menu_key,))
        await db.commit()


# ---------------- Stikerlar (hazilli auto-javob uchun global to'plam) ----------------

async def add_sticker(file_id: str, added_by: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO stickers (file_id, added_by) VALUES (?, ?)", (file_id, added_by)
        )
        await db.commit()
        return cursor.lastrowid


async def list_stickers():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM stickers ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_random_sticker():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT file_id FROM stickers ORDER BY RANDOM() LIMIT 1")
        row = await cursor.fetchone()
        return row[0] if row else None


async def delete_sticker(sticker_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM stickers WHERE id = ?", (sticker_id,))
        await db.commit()


async def count_stickers() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM stickers")
        row = await cursor.fetchone()
        return row[0] if row else 0
