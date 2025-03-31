#!/usr/bin/env python3
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from plugins import (
    admin,
    file_handler,
    auth,
    utils,
    shortener,
    database
)

# ASCII Art
with open("assets/cheetah_art.txt", "r") as f:
    print(f.read())

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
app = Client(
    "cheetah_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Error handler
async def error_handler(func, message, e):
    logger.error(f"Error in {func.__name__}: {str(e)}")
    await message.reply("⚠️ An error occurred. Please try again later.")

# Start command
@app.on_message(filters.command("start"))
async def start(client, message):
    try:
        if await auth.is_admin(message.from_user.id):
            await message.reply("👋 Admin mode activated!")
        else:
            await message.reply("👋 Welcome! Use /token to get access.")
    except Exception as e:
        await error_handler(start, message, e)

# Register other handlers
admin.register_handlers(app)
file_handler.register_handlers(app)
auth.register_handlers(app)

if __name__ == "__main__":
    logger.info("Starting Cheetah Bot...")
    app.run()

# Credit protection
if "Aryanwadhonkar/Cheetah" not in __file__ or "@wleaksOwner" not in Config.CREDIT:
    raise RuntimeError("Credits removed! Bot will not start.")
