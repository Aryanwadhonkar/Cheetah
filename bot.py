import os
import time
import logging
import secrets
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Optional

import pytz
from dotenv import load_dotenv
from telegram import (
    Update,
    InputMediaDocument,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message
)
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from pymongo import MongoClient, IndexModel

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
AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", 0))
PROTECT_CONTENT = os.getenv("PROTECT_CONTENT", "True").lower() == "true"
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", 24))
MONGO_URL = os.getenv("MONGO_URL")
URL_SHORTENER_API = os.getenv("URL_SHORTENER_API")
URL_SHORTENER_KEY = os.getenv("URL_SHORTENER_KEY")
URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN")

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
tokens.create_index([("expiry", 1)], expireAfterSeconds=0)

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

# URL Shortener (Only for token verification)
async def shorten_url(long_url: str) -> str:
    if not all([URL_SHORTENER_API, URL_SHORTENER_KEY, URL_SHORTENER_DOMAIN]):
        return long_url
    
    try:
        headers = {
            "Authorization": f"Bearer {URL_SHORTENER_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "long_url": long_url,
            "domain": URL_SHORTENER_DOMAIN
        }
        response = requests.post(
            URL_SHORTENER_API,
            json=data,
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("short_url", long_url)
    except Exception as e:
        logger.error(f"URL shortening failed: {e}")
    return long_url

# Auto-delete protected file sender
async def send_protected_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    try:
        msg = await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_id,
            protect_content=PROTECT_CONTENT
        )
        
        if AUTO_DELETE_TIME > 0:
            await asyncio.sleep(AUTO_DELETE_TIME * 60)
            await msg.delete()
    except Exception as e:
        logger.error(f"File send failed: {e}")

# Token verification handler
async def verify_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    if not args or len(args) < 1:
        await update.message.reply_text("Invalid link format")
        return
    
    # Admin/premium bypass
    if user.id in ADMINS or users.find_one({"user_id": user.id, "is_premium": True}):
        await send_protected_file(update, context, args[0])
        return
    
    # Token verification
    if len(args) > 1:
        token = args[1]
        if tokens.find_one({"user_id": user.id, "token": token, "expiry": {"$gt": datetime.now(pytz.utc)}}):
            await send_protected_file(update, context, args[0])
            return
    
    # Generate new token with shortened URL
    new_token = secrets.token_urlsafe(16)
    tokens.insert_one({
        "user_id": user.id,
        "token": new_token,
        "expiry": datetime.now(pytz.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    })
    
    verification_url = await shorten_url(
        f"https://t.me/{context.bot.username}?start={args[0]}_{new_token}"
    )
    
    await update.message.reply_text(
        f"🔒 Verification required: {verification_url}\n"
        f"Token expires in {TOKEN_EXPIRE_HOURS} hours",
        disable_web_page_preview=True
    )

# Existing commands (preserved)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Preserved existing start command"""
    await update.message.reply_text("Bot started! Use /help for commands")

async def getlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Preserved file upload handler"""
    # ... [existing getlink implementation]

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", verify_token))
    application.add_handler(CommandHandler("getlink", getlink))
    # ... [other preserved handlers]
    
    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
        raise
