#!/usr/bin/env python3
import os, subprocess, logging, datetime
from telegram import Bot
from googleapiclient.discovery import build

CHANNEL_ID   = os.getenv("CHANNEL_ID")
BOT_TOKEN    = os.getenv("BOT_TOKEN")
CHAT_ID      = os.getenv("CHAT_ID")
API_KEY      = os.getenv("YOUTUBE_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
bot = Bot(BOT_TOKEN)
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

def download_720p(video_id, title):
    outfile = "video.mp4"
    cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "-f", "bestvideo[height<=720]+bestaudio[ext=m4a]/best[height<=720]",
        "--merge-output-format", "mp4",
        "-o", outfile,
        "--no-progress",
        f"https://www.youtube.com/watch?v={video_id}"
    ]
    subprocess.run(cmd, check=True)
    sz = os.path.getsize(outfile) / 1024 / 1024
    logging.info("file size: %.1f MB", sz)
    if sz > 1900:
        raise RuntimeError("video > 1.9 GB – aborting to avoid artifact limit")
    return outfile

def send_telegram(file_path, title, descr):
    if len(descr) > 900:
        descr = descr[:900] + "…"
    with open(file_path, "rb") as fh:
        bot.send_video(CHAT_ID, video=fh,
                       caption=f"<b>{title}</b>\n\n{descr}",
                       parse_mode="HTML",
                       read_timeout=300, write_timeout=300)

def main():
    item = get_latest_ended_live()
    if not item:
        logging.info("no new ended live-stream")
        return
    vid, title, descr = item
    logging.info("found ended live: %s", title)
    file = download_720p(vid, title)
    logging.info("uploading to Telegram …")
    send_telegram(file, title, descr)
    os.remove(file)
    logging.info("done")

if __name__ == "__main__":
    main()