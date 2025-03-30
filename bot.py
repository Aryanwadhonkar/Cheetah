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
AUTO_DELETE = int(os.getenv("AUTO_DELETE_TIME", 0))
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", 24))
PROTECT_CONTENT = os.getenv("PROTECT_CONTENT", "True").lower() == "true"
MONGO_URL = os.getenv("DATABASE_URL")
URL_SHORTENER_API = os.getenv("URL_SHORTENER_API")
URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN")

# MongoDB Setup
client = MongoClient(MONGO_URL, tls=True, connectTimeoutMS=30000)
db = client.wleakfiles

# Collections
users = db.users
tokens = db.tokens
files = db.files

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

async def shorten_url(long_url: str) -> str:
    """Shorten URL only for token verification links"""
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

async def send_file_with_autodelete(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    """Send file with auto-delete and content protection"""
    try:
        sent_msg = await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_id,
            protect_content=PROTECT_CONTENT
        )
        
        if AUTO_DELETE > 0:
            await asyncio.sleep(AUTO_DELETE * 60)
            try:
                await sent_msg.delete()
            except Exception as e:
                logger.error(f"Failed to auto-delete: {e}")
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await update.message.reply_text("Failed to send file. Please try again.")

async def handle_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check if user is admin/premium
    if user.id in ADMINS or users.find_one({"user_id": user.id, "is_premium": True}):
        file_id = context.args[0] if context.args else None
        if file_id:
            await send_file_with_autodelete(update, context, file_id)
        return
    
    # Token verification with shortened URL
    if len(context.args) > 1 and context.args[1]:
        token = context.args[1]
        if tokens.find_one({"user_id": user.id, "token": token, "expiry": {"$gt": datetime.now(pytz.utc)}}):
            file_id = context.args[0]
            await send_file_with_autodelete(update, context, file_id)
            return
    
    # Generate new token with shortened URL
    token = secrets.token_urlsafe(16)
    expiry = datetime.now(pytz.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    tokens.insert_one({"user_id": user.id, "token": token, "expiry": expiry})
    
    # Create verification link with URL shortener
    bot_username = context.bot.username
    verification_url = await shorten_url(f"https://t.me/{bot_username}?start={context.args[0]}_{token}")
    
    await update.message.reply_text(
        f"🔒 Token required for access\n\n"
        f"Click here to verify: {verification_url}\n"
        f"Token valid for {TOKEN_EXPIRE_HOURS} hours",
        disable_web_page_preview=True
    )

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", handle_deep_link))
    # Add other handlers...
    application.run_polling()

if __name__ == "__main__":
    main()
