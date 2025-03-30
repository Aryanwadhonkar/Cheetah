import os
import time
import logging
import secrets
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict

import pytz
from dotenv import load_dotenv
from telegram import (
    Update,
    InputMediaDocument,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message
)
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError, BadRequest
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

# Constants from .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [int(admin.strip()) for admin in os.getenv("ADMINS").split(",") if admin.strip()]
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
FORCE_SUB = os.getenv("FORCE_SUB", "0")
AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", 0))
PROTECT_CONTENT = os.getenv("PROTECT_CONTENT", "True").lower() == "true"
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", 24))
MONGO_URI = os.getenv("MONGO_URI")  # Updated to MONGO_URI
URL_SHORTENER_API = os.getenv("URL_SHORTENER_API")
URL_SHORTENER_KEY = os.getenv("URL_SHORTENER_KEY")
URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN")
WHITELIST_IP = os.getenv("WHITELIST_IP", "")

# MongoDB Connection with error handling
try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        serverSelectionTimeoutMS=30000,
        retryWrites=False
    )
    db = client.get_database("wleakfiles")
    users = db.users
    tokens = db.tokens
    files = db.files
    premium = db.premium
    
    # Create indexes
    tokens.create_index([("expiry", 1)], expireAfterSeconds=0)
    logger.info("✅ MongoDB connected successfully")
except Exception as e:
    logger.critical(f"❌ MongoDB connection failed: {e}")
    # Fallback to dictionary storage
    db, users, tokens, files, premium = None, {}, {}, {}, {}
    logger.warning("⚠️ Using in-memory storage as fallback")

# ASCII Art
CHEETAH_ART = r"""
   ____ _    _ _____ _____ _______ _    _ 
  / ____| |  | |_   _|  __ \__   __| |  | |
 | |    | |__| | | | | |  | | | |  | |__| |
 | |    |  __  | | | | |  | | | |  |  __  |
 | |____| |  | |_| |_| |__| | | |  | |  | |
  \_____|_|  |_|_____|_____/  |_|  |_|  |_|
"""
print(CHEETAH_ART)

# Security Functions
async def verify_ip():
    """Check if current IP matches whitelist"""
    if not WHITELIST_IP:
        return True
        
    try:
        current_ip = requests.get('https://api.ipify.org', timeout=3).text
        if current_ip != WHITELIST_IP:
            logger.error(f"SECURITY ALERT: IP changed to {current_ip}")
            return False
        return True
    except:
        return True  # Fail open to avoid service disruption

# URL Shortener
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

# Core Bot Functions
async def send_protected_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    """Send file with auto-delete and protection"""
    try:
        msg = await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_id,
            protect_content=PROTECT_CONTENT,
            caption="🔒 Access granted | Don't share this file"
        )
        
        if AUTO_DELETE_TIME > 0:
            await asyncio.sleep(AUTO_DELETE_TIME * 60)
            try:
                await msg.delete()
                logger.info(f"Auto-deleted file for {update.effective_user.id}")
            except Exception as e:
                logger.error(f"Delete failed: {e}")
    except Exception as e:
        logger.error(f"File send failed: {e}")
        await update.message.reply_text("⚠️ Failed to send file. Try again later.")

async def verify_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Token verification handler"""
    if not await verify_ip():
        await update.message.reply_text("⚠️ Service temporarily unavailable")
        return
    
    user = update.effective_user
    args = context.args or []
    
    if len(args) < 1:
        await update.message.reply_text("Invalid link format")
        return
    
    file_id = args[0]
    
    # Admin/Premium bypass
    if user.id in ADMINS or (db and premium.find_one({"user_id": user.id})):
        await send_protected_file(update, context, file_id)
        return
    
    # Token verification
    if len(args) > 1 and db:
        token = args[1]
        if tokens.find_one({"user_id": user.id, "token": token, "expiry": {"$gt": datetime.now(pytz.utc)}}):
            await send_protected_file(update, context, file_id)
            return
    
    # Generate new token
    new_token = secrets.token_urlsafe(16)
    if db:
        tokens.insert_one({
            "user_id": user.id,
            "token": new_token,
            "expiry": datetime.now(pytz.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
            "ip": WHITELIST_IP
        })
    
    verification_url = await shorten_url(
        f"https://t.me/{context.bot.username}?start={file_id}_{new_token}"
    )
    
    await update.message.reply_text(
        f"🔐 <b>Verification Required</b>\n\n"
        f"<a href='{verification_url}'>Click here to verify</a>\n"
        f"Token valid for {TOKEN_EXPIRE_HOURS} hours",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

# Admin Commands
async def getlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """File upload handler"""
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ Admin access required")
        return
    
    try:
        file = update.message.reply_to_message.document
        msg = await context.bot.send_document(
            chat_id=CHANNEL_ID,
            document=file.file_id,
            caption=f"📁 {file.file_name}\n⬆️ Uploaded by @{update.effective_user.username}"
        )
        
        if db:
            files.insert_one({
                "file_id": file.file_id,
                "message_id": msg.message_id,
                "uploader": update.effective_user.id,
                "timestamp": datetime.now(pytz.utc)
            })
        
        access_url = f"https://t.me/{context.bot.username}?start={file.file_id}"
        await update.message.reply_text(
            f"✅ File stored!\n\n<code>{access_url}</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        await update.message.reply_text("⚠️ Failed to store file")

# System Functions
async def maintenance_task():
    """Background maintenance"""
    while True:
        try:
            if db:
                # Clean expired tokens
                result = tokens.delete_many({"expiry": {"$lt": datetime.now(pytz.utc)}})
                if result.deleted_count > 0:
                    logger.info(f"Cleaned {result.deleted_count} expired tokens")
            
            await asyncio.sleep(3600)  # Run hourly
        except Exception as e:
            logger.error(f"Maintenance task failed: {e}")
            await asyncio.sleep(60)

def main():
    if not BOT_TOKEN:
        logger.critical("❌ BOT_TOKEN not found in .env")
        return
    
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .post_init(lambda _: asyncio.create_task(maintenance_task())) \
        .build()
    
    # Handlers
    application.add_handler(CommandHandler("start", verify_token))
    application.add_handler(CommandHandler("getlink", getlink, filters.Document.ALL))
    
    # Error handler
    application.add_error_handler(lambda u, c: logger.error(f"Update {u} caused error {c.error}"))
    
    logger.info("🤖 Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        exit(1)
