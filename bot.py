#!/usr/bin/env python3
"""
A simple Telegram bot for downloading videos from supported websites and sending them back to the user.

This bot uses the python‑telegram‑bot library (v20) for interacting with the Telegram Bot API and yt_dlp
for downloading videos.  To run this bot, install the dependencies listed in requirements.txt and set
your bot token in the BOT_TOKEN variable below.

Usage:

    python bot.py

After running, open your bot on Telegram and send it a video URL (e.g. a YouTube link).  The bot will
download the video and send it back to you as a video message or a document if it exceeds the video
size limit for bots.

"""

import asyncio
import logging
import os
import re
import tempfile
from contextlib import suppress
from typing import Optional

from yt_dlp import YoutubeDL, utils as yt_utils

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


##############################
#  Bot configuration
##############################

# Replace this with your own bot token from BotFather.
# # BOT_TOKEN: str = "7887617387:AAEiVhYpyFNrCPULpdqVCAsBgSiwFmhzvmE"

# Regular expression to validate HTTP(S) URLs.  Basic check to ensure user sent something that
# BOT_TOKEN: str = "7887617387:AAHjfgyYB1_1MjvnIsGa2qs4TyAgnsiqOXM"
# # BOT_TOKEN: str = 7887617387:AAHjfgyYB1_1MjvnIsGa2qs4TyAgnsiqOXM"
BOT_TOKEN: str = "7887617387:AAHjfgyYB1_1MjvnIsGa2qs4TyAgnsiqOXM"

# resembles a URL.  More sophisticated validation can be added as needed.
URL_REGEX = re.compile(r"https?://\S+")

# Directory for storing downloaded files temporarily.  Using system temp directory keeps files out
# of the project tree and ensures they are cleaned up automatically when the OS purges temp files.
TEMP_DIR = tempfile.gettempdir()

# Configure logging to output debug information to stdout.  This helps with debugging issues when
# running the bot.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


##############################
#  Helper functions
##############################

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing path separators and unsafe characters."""
    return re.sub(r"[\\/\:*?\"<>|]", "_", filename)


def download_video(url: str) -> Optional[str]:
    """
    Download a video from the given URL using yt_dlp.

    Returns the path to the downloaded file if successful, or None otherwise.

    The function chooses the best available format and merges audio and video into an MP4 file.
    Files are saved to the system temporary directory.
    """
    logger.info("Downloading video from %s", url)
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        # Specify output template.  %(title)s is sanitized by yt-dlp; we add a random suffix to avoid collisions.
        "outtmpl": os.path.join(TEMP_DIR, "%(title).64s.%(ext)s"),
        "noplaylist": True,  # Do not download playlists or multiple entries
        "quiet": True,
        "no_warnings": True,
        # Ensure video and audio are merged into a single file when possible
        "merge_output_format": "mp4",
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Determine the downloaded filename.  yt-dlp writes to outtmpl; use prepare_filename() for exact file name.
            filename = ydl.prepare_filename(info)
            sanitized = sanitize_filename(filename)
            # yt-dlp may rename files; check if merged file exists (e.g. .mkv or .mp4) and return that.
            if os.path.exists(filename):
                return filename
            # If file doesn't exist, attempt to find by extension
            base, _ext = os.path.splitext(filename)
            for ext in (".mp4", ".mkv", ".webm", ".m4a"):
                alt = base + ext
                if os.path.exists(alt):
                    return alt
    except yt_utils.DownloadError as e:
        logger.error("DownloadError: %s", e)
    except Exception as e:
        logger.exception("Unexpected error during download: %s", e)
    return None


##############################
#  Handler functions
##############################

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /start command."""
    logger.info("Received /start command from user %s", update.effective_user.id)
    message = (
        "Hello! 👋\n\n"
        "I am a video downloader bot. Send me a video URL (e.g. a YouTube link), and I will download the "
        "video and send it back to you.\n\n"
        "*Please note*: The download might take some time depending on the file size and network speed."
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages that may contain video URLs."""
    if not update.message:
        return
    text = update.message.text or ""
    user_id = update.effective_user.id if update.effective_user else "unknown"
    logger.info("Received message from user %s: %s", user_id, text)
    match = URL_REGEX.search(text)
    if not match:
        await update.message.reply_text(
            "Please send me a valid video URL starting with http or https."
        )
        return
    url = match.group(0)
    # Notify the user that the download is starting
    await update.message.reply_chat_action(ChatAction.UPLOAD_VIDEO)
    await update.message.reply_text(f"Downloading video...\nURL: {url}")
    # Perform download in a thread to avoid blocking the event loop
    loop = asyncio.get_running_loop()
    file_path = await loop.run_in_executor(None, download_video, url)
    if not file_path:
        await update.message.reply_text(
            "Sorry, I couldn't download the video. Please make sure the URL is correct and try again."
        )
        return
    # Determine file size and choose whether to send as video or document
    file_size = os.path.getsize(file_path)
    # Telegram bots can send videos up to 50 MB using send_video; for larger files, send as document (up to 2 GB)
    try:
        with open(file_path, "rb") as f:
            if file_size <= 50 * 1024 * 1024:
                logger.info("Sending video file %s (%d bytes) to user %s", file_path, file_size, user_id)
                await update.message.reply_chat_action(ChatAction.UPLOAD_VIDEO)
                await update.message.reply_video(video=f, caption="Here is your video!")
            else:
                logger.info("Sending document file %s (%d bytes) to user %s", file_path, file_size, user_id)
                await update.message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
                await update.message.reply_document(document=f, filename=os.path.basename(file_path), caption="Here is your video (sent as a document due to size).")
    except Exception as e:
        logger.exception("Error sending file to user %s: %s", user_id, e)
        await update.message.reply_text(
            "Sorry, something went wrong while sending the video. Please try again later."
        )
    finally:
        # Clean up downloaded file to conserve disk space
        with suppress(Exception):
            os.remove(file_path)


##############################
#  Main entry point
##############################

def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "Bot token is not set. Please replace BOT_TOKEN with your actual bot token from BotFather."
        )
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Run the bot until Ctrl+C is pressed
    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    main()
