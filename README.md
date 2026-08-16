# 🕸 Spidey Hub — Spider-Man mavzusidagi Telegram bot + Mini App

## Nima bor?

- **Bot** (`bot/`) — aiogram 3 asosida, 6 ta bo'lim: Filmlar, Seriallar, Multfilmlar, Stikerlar, Emojilar, Videolar
- **Admin panel** — `/admin` orqali kontent qo'shish, o'chirish, statistika, hammaga xabar yuborish
- **Majburiy obuna** — kanalga a'zo bo'lmagan foydalanuvchi botdan foydalana olmaydi
- **Mini App** (`webapp/index.html`) — Spider-Man uslubidagi animatsiyali interfeys (web-chiziqlar, tovush effekti, vibratsiya)
- SQLite baza — qo'shimcha serverga hojat yo'q

> ⚠️ **Eslatma**: Kontent sifatida (filmlar/seriallar) faqat o'zingiz huquqiga ega bo'lgan yoki tarqatishga ruxsat berilgan materiallarni joylang. Marvel/Sony'ga tegishli original filmlarni ruxsatsiz tarqatish mualliflik huquqini buzadi.

---

## 1-qadam: BotFather'da bot yaratish

1. Telegram'da [@BotFather](https://t.me/BotFather) ga o'ting
2. `/newbot` yuboring, nom va username bering
3. Sizga beriladigan **TOKEN**ni saqlab qo'ying

## 2-qadam: Kanal tayyorlash (majburiy obuna uchun)

1. Yopiq yoki ochiq kanal yarating (masalan `@spidey_hub_kanal`)
2. Botingizni kanalga **admin** qilib qo'shing
3. Kanal ID sini olish uchun kanalga istalgan xabar tashlang, so'ng shu xabarni [@userinfobot](https://t.me/userinfobot) ga forward qiling — u sizga `-100...` ko'rinishidagi ID beradi

## 3-qadam: Loyihani GitHub'ga yuklash

```bash
cd spiderman_bot
git init
git add .
git commit -m "Spidey Hub bot - initial commit"
git branch -M main
git remote add origin https://github.com/<username>/spiderman-bot.git
git push -u origin main
```

> `.env` faylini hech qachon GitHub'ga yubormang — u `.gitignore`da bo'lishi kerak (pastda ko'rsatilgan).

## 4-qadam: Railway'da deploy qilish

1. [railway.app](https://railway.app) ga kiring → **New Project** → **Deploy from GitHub repo**
2. `spiderman-bot` repo'ni tanlang — Railway avtomatik `Dockerfile`ni topib quradi
3. Loyiha ochilgach, **Variables** bo'limiga o'ting va quyidagilarni qo'shing:
   - `BOT_TOKEN` — BotFather bergan token
   - `ADMIN_IDS` — sizning Telegram user ID'ingiz (bilmasangiz [@userinfobot](https://t.me/userinfobot)dan oling)
   - `CHANNEL_USERNAME` — `@sizning_kanalingiz`
   - `CHANNEL_ID` — 2-qadamda olingan `-100...` ID
4. **Settings → Networking → Generate Domain** tugmasini bosing — sizga `https://xxx.up.railway.app` domeni beriladi
5. Shu domenni nusxalab, yana **Variables**ga qaytib `WEBAPP_URL` qiymatini o'sha domen bilan to'ldiring (masalan `https://xxx.up.railway.app`)
6. Railway avtomatik qayta deploy qiladi — **Deployments** bo'limidan logni kuzatib boring, `Bot polling boshlandi 🕸` yozuvini ko'rsangiz — tayyor

## 5-qadam: Mini App'ni BotFather'da ulash (ixtiyoriy, lekin tavsiya etiladi)

1. @BotFather → botingizni tanlang → **Bot Settings → Menu Button**
2. **Configure Menu Button** → URL sifatida Railway domeningizni kiriting
3. Endi foydalanuvchilar bot chatining pastida "Menu" tugmasi orqali ham Mini App'ni ocha oladi

## 6-qadam: Kontent qo'shish

1. Botga `/admin` yuboring (faqat `ADMIN_IDS`dagi ID uchun ishlaydi)
2. **➕ Kontent qo'shish** → kategoriya tanlang → media fayl yuboring → nom va tavsif kiriting
3. Tayyor! Kontent bir zumda bot va Mini App'da ko'rinadi

---

## Admin panel — to'liq funksiyalar ro'yxati

| Funksiya | Kimga ochiq | Tavsif |
|---|---|---|
| ➕ Kontent qo'shish | super + moderator | Kategoriya tanlab media yuklash |
| ✏️ Kontent tahrirlash | super + moderator | ID orqali nom/tavsifni o'zgartirish |
| 📋 Kontent ro'yxati | super + moderator | Har bo'limdagi kontentlar ID bilan |
| 🗑 Kontent o'chirish | super + moderator | ID orqali o'chirish |
| 📊 Statistika | super + moderator | Bo'limlar bo'yicha son + foydalanuvchilar soni |
| 🖼 Menyu rasmlari | super + moderator | Har bir menyu (asosiy + 6 bo'lim) tepasiga rasm o'rnatish/o'chirish |
| 📣 Xabar yuborish | faqat super | Barcha foydalanuvchilarga broadcast |
| 👤 Adminlar | faqat super | Yangi admin qo'shish/o'chirish, rolini belgilash (👑 super / 🛡 moderator) |
| 📢 Kanallar | faqat super | Majburiy obuna uchun bir nechta kanal qo'shish/o'chirish |

**Muhim eslatishlar:**
- Birinchi marta ishga tushirganda `.env`dagi `ADMIN_IDS` avtomatik **super admin** sifatida bazaga yoziladi. Shundan keyin yangi adminlarni to'g'ridan-to'g'ri bot ichidan (**👤 Adminlar**) qo'shishingiz mumkin — `.env`ni qayta o'zgartirish shart emas.
- **🖼 Menyu rasmlari**: bu yerga yuklagan rasmingiz o'sha menyu (masalan "Filmlar" bo'limi) ochilganda doim tepada ko'rinadi. Rasmni o'zingiz tanlaysiz — Marvel/Sony'ga tegishli original suratlarni ruxsatsiz tarqatishdan saqlaning; fan-art yoki o'zingiz tayyorlagan grafika xavfsizroq variant.
- **📢 Kanallar**: qo'shgan har bir kanalingizda bot **admin** bo'lishi shart, aks holda obuna tekshiruvi ishlamaydi.

---

## Lokal test qilish (ixtiyoriy)

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # so'ng .env faylini to'ldiring
python -m bot.main
```

## .gitignore (loyihaga qo'shing)

```
.env
*.db
__pycache__/
venv/
```

---

## Keyingi qadamlar uchun g'oyalar

- Har bir kontentga rasm-thumbnail qo'shish (Mini App kartochkalarida ko'rsatish uchun)
- Kunlik "Kun kontenti" push-xabari (broadcast funksiyasi orqali)
- Referal tizimi qo'shish (avvalgi botlaringizdagi pattern asosida)
- Instagram'dan avtomatik kontent tortib olish uchun Meta Graph API integratsiyasi
