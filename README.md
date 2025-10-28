# YouTube-Live → Telegram Archiver (GitHub Actions)

Automatically download **ended YouTube live-streams** (≤ 720p, < 2 GB) and upload them to a **Telegram channel** within **30 minutes** of broadcast end.  
Runs **only between 6 AM – 12 PM IST** every 30 min via GitHub Actions → **100 % free, zero server maintenance**.

---

## ✅ Features
| Feature | Status |
|---------|--------|
| Checks for **ended** live streams (not normal uploads) | ✅ |
| Downloads **720p** to keep file < 2 GB (GitHub limit) | ✅ |
| Uploads to **Telegram** with original title + description | ✅ |
| **Scheduled** 6 AM – 12 PM IST (UTC 0-6) every 30 min | ✅ |
| **Dry-run workflow** to test secrets before first real run | ✅ |
| No local storage / repo stays tiny | ✅ |

---

## 🚀 Quick Start
1. [Create Telegram bot & get channel ID](#1-telegram-setup)
2. [Get YouTube Data API key & channel ID](#2-youtube-setup)
3. [Add secrets to GitHub](#3-github-secrets)
4. Push this repo → Actions tab → run **dry-run** → ✅ → done!

---

## 1. Telegram Setup
1. Message **[@BotFather](https://t.me/BotFather)** → `/newbot`  
2. Copy **HTTP API token** (`123456:ABC...`) → save as **`<BOT_TOKEN>`**  
3. Add the bot as **Admin** to your target channel  
4. Send any message in the channel → visit:  
   `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`  
5. Copy `"id":-1001234567890` → save as **`<CHAT_ID>`**

---

## 2. YouTube Setup
1. [Google Cloud Console](https://console.cloud.google.com) → new project → enable **YouTube Data API v3**  
2. **Credentials → Create API key** → save as **`<YOUTUBE_API_KEY>`**  
3. Get the **channel id** you want to monitor:  
   - Open channel page → view-source → search `"channelId":"UC...`  
   - save as **`<CHANNEL_ID>`**

---

## 3. GitHub Secrets
In your **fork** → **Settings → Secrets → Actions → New secret**

| Name | Value |
|------|-------|
| `BOT_TOKEN` | `<BOT_TOKEN>` |
| `CHAT_ID` | `<CHAT_ID>` |
| `YOUTUBE_API_KEY` | `<YOUTUBE_API_KEY>` |
| `CHANNEL_ID` | `<CHANNEL_ID>` |

---

## 4. Test Before Going Live
Actions tab → **"🔍 Dry-run test"** → **Run workflow**  
You should receive a **test message** in Telegram and see API/size checks pass.

---

## 5. Enjoy
The **real workflow** now runs automatically **every 30 min between 6 AM – 12 PM IST**.  
Each ended live-stream lands in your Telegram channel within minutes.

---

## 📂 Repository Layout
```
.github/workflows/
├── archive.yml      # production cron job
└── dry-run.yml      # manual safety check
archive.py           # downloader + uploader
requirements.txt     # Python deps (empty list)
README.md            # this file
```

---

## 🛠️ Customise
- **Quality**: edit `height<=720` → `480` in `archive.py`  
- **Time window**: change cron line in `archive.yml`  
- **Size guard**: raise abort limit (keep < 2 GB)  
- **Extra backup**: add `rclone` step after Telegram upload

---

## ⚠️ Limits
- GitHub **artifact** & **runner** disk: **2 GB hard** → script aborts if estimate > 1.9 GB  
- **Runtime**: 6 h max (1-hour 720 p stream ≈ 600-900 MB → safe)  
- **API quota**: 10 000 units/day → ~200 checks (plenty)

---

## 📄 License
MIT — feel free to fork & improve.

---

Like it? ⭐ the repo and share your tweaks!
