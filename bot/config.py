import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Bir nechta admin ID larini vergul bilan ajratib yozing: 111111,222222
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# Boshlang'ich majburiy obuna kanali (keyinchalik /admin panelidan ko'proq qo'shsa bo'ladi)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")

# Mini App joylashtirilgan URL (Railway/Netlify domeningiz)
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

PORT = int(os.getenv("PORT", "8080"))

DB_PATH = os.getenv("DB_PATH", "spiderman_bot.db")

# Kontent kategoriyalari
CATEGORIES = {
    "filmlar": {"title": "Filmlar", "emoji": "🎬"},
    "seriallar": {"title": "Seriallar", "emoji": "📺"},
    "multfilmlar": {"title": "Multfilmlar", "emoji": "🎨"},
    "stikerlar": {"title": "Stikerlar", "emoji": "🖼"},
    "emojilar": {"title": "Emojilar", "emoji": "😀"},
    "videolar": {"title": "Videolar", "emoji": "🎥"},
}
