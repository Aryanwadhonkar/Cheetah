import os
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import Database
from shortener import shorten_url
import asyncio
import logging
logging.basicConfig(level=logging.INFO)

# Initialize
app = Client(
    "CheetahBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    sleep_threshold=30
)
db = Database(app)

# [Paste ALL your original command handlers here]
# start(), getlink(), broadcast(), ban_user(), etc.

if __name__ == "__main__":
    print(r"""
   ____ _    _ ______ _____ _______ _____ _    _ 
  / ____| |  | |  ____|  __ \__   __|_   _| |  | |
 | |    | |__| | |__  | |__) | | |    | | | |__| |
 | |    |  __  |  __| |  _  /  | |    | | |  __  |
 | |____| |  | | |____| | \ \  | |   _| |_| |  | |
  \_____|_|  |_|______|_|  \_\ |_|  |_____|_|  |_|
    """)
    app.run()
