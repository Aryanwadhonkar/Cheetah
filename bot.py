import os
import time
import logging
import secrets
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytz
from dotenv import load_dotenv
from telegram import (
    Update,
    InputMediaDocument,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions
)
from telegram.constants import ChatAction, ChatMemberStatus
from telegram.error import TelegramError, BadRequest, Forbidden, RetryAfter
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from pymongo import MongoClient, IndexModel
from pymongo.errors import PyMongoError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS").split(",")))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
FORCE_SUB = os.getenv("FORCE_SUB", "0")
AUTO_DELETE = int(os.getenv("AUTO_DELETE_TIME", 0))
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))  # New variable
MONGO_URL = os.getenv("DATABASE_URL")
URL_SHORTENER_API = os.getenv("URL_SHORTENER_API")
URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN")
FORCE_SUB_TEXT = os.getenv("FORCE_SUB_TEXT", "🔹 Please join our channel to use this bot")  # Custom message

# MongoDB Setup
client = MongoClient(
    MONGO_URL,
    tls=True,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
    serverSelectionTimeoutMS=30000
)
db = client.wleakfiles

# Collections
users = db.users
tokens = db.tokens
files = db.files
premium = db.premium

# Create indexes
users.create_index([("user_id", 1)], unique=True)
tokens.create_index([("expiry", 1)], expireAfterSeconds=0)  # Auto-expire tokens
files.create_index([("file_id", 1)], unique=True)

# ASCII Art
CHEETAH_ART = """
   ____ _    _ _____ _____ _______ _    _ 
  / ____| |  | |_   _|  __ \__   __| |  | |
 | |    | |__| | | | | |  | | | |  | |__| |
 | |    |  __  | | | | |  | | | |  |  __  |
 | |____| |  | |_| |_| |__| | | |  | |  | |
  \_____|_|  |_|_____|_____/  |_|  |_|  |_|
"""
print(CHEETAH_ART)

# Enhanced URL Shortener
async def shorten_url(long_url: str) -> str:
    if not URL_SHORTENER_API or not URL_SHORTENER_DOMAIN:
        return long_url
    
    try:
        response = requests.post(
            URL_SHORTENER_API,
            json={"long_url": long_url},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            return f"https://{URL_SHORTENER_DOMAIN}/{response.json().get('short_code')}"
    except Exception as e:
        logger.error(f"URL shortening failed: {e}")
    return long_url

# Force Subscribe with Custom Message
async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if FORCE_SUB == "0":
        return True
    
    user = update.effective_user
    try:
        chat_member = await context.bot.get_chat_member(FORCE_SUB, user.id)
        if chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"{FORCE_SUB_TEXT}\n\nJoin: https://t.me/{FORCE_SUB}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_SUB}")
                ]])
            )
            return False
        return True
    except Exception as e:
        logger.error(f"Force sub check failed: {e}")
        return True

# Token Generation with Configurable Expiry
async def generate_token(user_id: int) -> str:
    token = secrets.token_urlsafe(16)
    expiry = datetime.now(pytz.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    
    tokens.update_one(
        {"user_id": user_id},
        {"$set": {"token": token, "expiry": expiry}},
        upsert=True
    )
    return token

# Modified Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Force sub check
    if not await check_force_sub(update, context):
        return
    
    if await is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    
    if await is_admin(user.id) or await is_premium(user.id):
        await update.message.reply_text("👋 Admin/Premium access detected! Use /getlink to upload files.")
    else:
        token = await generate_token(user.id)
        await update.message.reply_text(
            f"🔑 Your access token (valid for {TOKEN_EXPIRE_HOURS} hours):\n\n"
            f"`{token}`\n\n"
            "Use this with file links to access content.",
            parse_mode="Markdown"
        )

# [Rest of your existing handlers with these new integrations...]

def main():
    try:
        # Verify MongoDB connection
        client.server_info()
        logger.info("Connected to MongoDB successfully")
        
        # Create application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("getlink", getlink))
        # ... [add other handlers]
        
        application.add_error_handler(error_handler)
        
        # Run the bot
        application.run_polling()
    except PyMongoError as e:
        logger.error(f"MongoDB connection failed: {e}")
    except Exception as e:
        logger.error(f"Bot startup failed: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
