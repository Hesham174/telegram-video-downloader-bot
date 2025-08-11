# Telegram Video Downloader Bot

This repository contains a simple Telegram bot written in Python that can download videos from supported websites (e.g., YouTube) and send them back to the user via Telegram.

## Features

- Built with [`python‑telegram‑bot`](https://python-telegram-bot.readthedocs.io/).
- Uses [`yt_dlp`](https://github.com/yt-dlp/yt-dlp), a modern fork of `youtube-dl`, to download videos.
- Responds to any message that contains a URL; if the URL points to a downloadable video, the bot downloads the highest quality video available and returns it to the user as a video file or a document (depending on Telegram size limits).
- Provides a `/start` command to greet users and explain how to use the bot.

## Setup

1. **Install dependencies**

   The bot depends on `python-telegram-bot` v20 and `yt_dlp`.  Install them with pip:

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your bot token**

   In `bot.py`, replace the value of `BOT_TOKEN` with the token you obtained from [BotFather](https://t.me/botfather) when creating your Telegram bot.  _Do not share your token publicly!_

3. **Run the bot**

   Execute the following command in your terminal:

   ```bash
   python bot.py
   ```

   The bot will start and listen for messages.  Send a video URL to your bot in Telegram, and it will download and send the video back to you.

## Notes

- Telegram imposes a maximum file size for bots (currently 50 MB for video messages and up to 2000 MB for documents).  If the downloaded video exceeds the size limit for videos, the bot attempts to send it as a document instead.
- Downloaded files are temporarily stored in the system’s temporary directory and removed after being sent to the user.
