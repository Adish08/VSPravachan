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
    temp_file = "audio_temp.m4a"
    outfile = "audio.m4a"
    
    # Step 1: Download audio
    cmd_download = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "-f", "bestaudio/best",
        "-x",
        "--audio-format", "m4a",
        "-o", temp_file,
        "--no-progress",
        f"https://www.youtube.com/watch?v={video_id}"
    ]
    subprocess.run(cmd_download, check=True)
    logging.info("download complete, re-encoding to reduce size...")
    
    # Step 2: Re-encode with aggressive compression
    cmd_compress = [
        "ffmpeg", "-i", temp_file,
        "-ac", "1",           # mono
        "-ar", "22050",       # 22kHz sample rate
        "-b:a", "16k",        # 16kbps bitrate
        "-y",                 # overwrite output
        outfile
    ]
    subprocess.run(cmd_compress, check=True, capture_output=True)
    
    # Clean up temp file
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    sz = os.path.getsize(outfile) / 1024 / 1024
    logging.info("compressed file size: %.1f MB", sz)
    if sz > 48:
        raise RuntimeError("audio > 48 MB – aborting to stay under Telegram bot limit")
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
    
    try:
        file = download_audio(vid, title)
        logging.info("download complete, file: %s", file)
        
        if not os.path.exists(file):
            raise FileNotFoundError(f"Downloaded file not found: {file}")
        
        logging.info("uploading to Telegram …")
        await send_telegram(file, title, descr)
        logging.info("upload complete")
        
        os.remove(file)
        logging.info("done - file cleaned up")
    except Exception as e:
        logging.error("Error: %s", e, exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())