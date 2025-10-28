#!/usr/bin/env python3
import os, subprocess, logging, datetime, asyncio
from telegram import Bot
from googleapiclient.discovery import build

CHANNEL_ID   = os.getenv("CHANNEL_ID")
BOT_TOKEN    = os.getenv("BOT_TOKEN")
CHAT_ID      = os.getenv("CHAT_ID")
API_KEY      = os.getenv("YOUTUBE_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
youtube = build("youtube", "v3", developerKey=API_KEY)

def get_latest_ended_live():
    req = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        eventType="completed",
        type="video",
        order="date",
        maxResults=1
    )
    res = req.execute()
    if res["items"]:
        v = res["items"][0]
        return v["id"]["videoId"], v["snippet"]["title"], v["snippet"]["description"]
    return None

def download_audio(video_id, title):
    outfile = "audio.m4a"
    cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "-f", "bestaudio/best",
        "-x",  # extract audio
        "--audio-format", "m4a",
        "--audio-quality", "32k",
        "--postprocessor-args", "ffmpeg:-b:a 32k",
        "-o", outfile,
        "--no-progress",
        f"https://www.youtube.com/watch?v={video_id}"
    ]
    subprocess.run(cmd, check=True)
    sz = os.path.getsize(outfile) / 1024 / 1024
    logging.info("file size: %.1f MB", sz)
    if sz > 45:
        raise RuntimeError("audio > 45 MB – aborting to stay under Telegram bot limit")
    return outfile

async def send_telegram(file_path, title, descr):
    bot = Bot(BOT_TOKEN)
    if len(descr) > 900:
        descr = descr[:900] + "…"
    with open(file_path, "rb") as fh:
        await bot.send_audio(CHAT_ID, audio=fh,
                             title=title,
                             caption=descr,
                             parse_mode="HTML",
                             read_timeout=300, write_timeout=300)

async def main():
    item = get_latest_ended_live()
    if not item:
        logging.info("no new ended live-stream")
        return
    vid, title, descr = item
    logging.info("found ended live: %s", title)
    file = download_audio(vid, title)
    logging.info("uploading to Telegram …")
    await send_telegram(file, title, descr)
    os.remove(file)
    logging.info("done")

if __name__ == "__main__":
    asyncio.run(main())