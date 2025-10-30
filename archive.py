#!/usr/bin/env python3
import os, subprocess, logging, datetime, asyncio
from telegram import Bot
from googleapiclient.discovery import build
import json

CHANNEL_ID   = os.getenv("CHANNEL_ID")
BOT_TOKEN    = os.getenv("BOT_TOKEN")
CHAT_ID      = os.getenv("CHAT_ID")
API_KEY      = os.getenv("YOUTUBE_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
youtube = build("youtube", "v3", developerKey=API_KEY)

PROCESSED_FILE = "processed_videos.json"

def load_processed_videos():
    """Load the list of already processed video IDs"""
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, 'r') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()
    return set()

def save_processed_video(video_id):
    """Add a video ID to the processed list"""
    processed = load_processed_videos()
    processed.add(video_id)
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(list(processed), f, indent=2)
    logging.info("Marked video %s as processed", video_id)

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
        video_id = v["id"]["videoId"]
        
        # Get additional video details (duration, publish date)
        video_req = youtube.videos().list(
            part="contentDetails,snippet",
            id=video_id
        )
        video_res = video_req.execute()
        video_data = video_res["items"][0]
        
        return {
            "id": video_id,
            "title": video_data["snippet"]["title"],
            "description": video_data["snippet"]["description"],
            "published_at": video_data["snippet"]["publishedAt"],
            "duration": video_data["contentDetails"]["duration"]
        }
    return None

def parse_duration(iso_duration):
    """Convert ISO 8601 duration (PT1H30M15S) to readable format"""
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return "Unknown"
    hours, minutes, seconds = match.groups()
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return " ".join(parts) if parts else "0s"

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
    
    # Step 2: Re-encode with compression
    cmd_compress = [
        "ffmpeg", "-i", temp_file,
        "-ac", "1",           # mono
        "-ar", "24000",       # 24kHz sample rate
        "-b:a", "32k",        # 32kbps bitrate
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
    return outfile, sz

async def send_telegram(file_path, video_info, file_size_mb):
    bot = Bot(BOT_TOKEN)
    
    # Parse date
    from datetime import datetime
    pub_date = datetime.fromisoformat(video_info["published_at"].replace('Z', '+00:00'))
    date_str = pub_date.strftime("%d %B %Y")
    
    # Parse duration
    duration_str = parse_duration(video_info["duration"])
    
    # Format description (truncate if too long)
    description = video_info["description"]
    if len(description) > 500:
        description = description[:500] + "…"
    
    # Build caption
    caption = f"""<b>{video_info['title']}</b>

📅 Date: {date_str}
⏱ Duration: {duration_str}
💾 Size: {file_size_mb:.1f} MB

{description}"""
    
    with open(file_path, "rb") as fh:
        await bot.send_audio(CHAT_ID, audio=fh,
                             title=video_info['title'],
                             caption=caption,
                             parse_mode="HTML",
                             read_timeout=300, write_timeout=300)

async def main():
    video_info = get_latest_ended_live()
    if not video_info:
        logging.info("no new ended live-stream")
        return
    
    # Check if this video has already been processed
    processed_videos = load_processed_videos()
    if video_info['id'] in processed_videos:
        logging.info("Video %s already processed, skipping", video_info['id'])
        return
    
    logging.info("found ended live: %s", video_info['title'])
    
    try:
        file, file_size_mb = download_audio(video_info['id'], video_info['title'])
        logging.info("download complete, file: %s", file)
        
        if not os.path.exists(file):
            raise FileNotFoundError(f"Downloaded file not found: {file}")
        
        logging.info("uploading to Telegram …")
        await send_telegram(file, video_info, file_size_mb)
        logging.info("upload complete")
        
        # Mark video as processed after successful upload
        save_processed_video(video_info['id'])
        
        os.remove(file)
        logging.info("done - file cleaned up")
    except Exception as e:
        logging.error("Error: %s", e, exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())