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
from pymongo.errors import PyMongoError, ConnectionFailure

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
WHITELIST_IP = os.getenv("WHITELIST_IP")

# MongoDB Setup with IP verification
def get_mongo_client():
    try:
        current_ip = requests.get('https://api.ipify.org', timeout=3).text
        if current_ip != WHITELIST_IP:
            raise ConnectionError(f"IP mismatch! Current: {current_ip} | Allowed: {WHITELIST_IP}")
        
        return MongoClient(
            MONGO_URL,
            tls=True,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            serverSelectionTimeoutMS=10000,
            appName="CheetahBot",
            retryWrites=False
        )
    except Exception as e:
        logger.critical(f"MongoDB connection failed: {e}")
        raise

try:
    client = get_mongo_client()
    db = client.wleakfiles
    users = db.users
    tokens = db.tokens
    files = db.files
    premium = db.premium
    tokens.create_index([("expiry", 1)], expireAfterSeconds=0)
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    exit(1)

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

# Security Functions
async def verify_ip():
    """Check if current IP matches whitelist"""
    try:
        current_ip = requests.get('https://api.ipify.org', timeout=3).text
        if current_ip != WHITELIST_IP:
            logger.error(f"SECURITY ALERT: IP changed to {current_ip}")
            return False
        return True
    except:
        return True  # Fail open to avoid service disruption

# URL Shortener (Secure Implementation)
async def shorten_url(long_url: str) -> str:
    if not all([URL_SHORTENER_API, URL_SHORTENER_KEY, URL_SHORTENER_DOMAIN]):
        return long_url
    
    try:
        headers = {
            "Authorization": f"Bearer {URL_SHORTENER_KEY}",
            "Content-Type": "application/json",
            "X-Requested-With": "TelegramBot"
        }
        data = {
            "long_url": long_url,
            "domain": URL_SHORTENER_DOMAIN,
            "expire_after": f"{TOKEN_EXPIRE_HOURS}h"  # Match token expiry
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
    """Enhanced token verification with IP checks"""
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
    if user.id in ADMINS or premium.find_one({"user_id": user.id}):
        await send_protected_file(update, context, file_id)
        return
    
    # Token verification
    if len(args) > 1:
        token = args[1]
        if tokens.find_one({"user_id": user.id, "token": token, "expiry": {"$gt": datetime.now(pytz.utc)}}):
            await send_protected_file(update, context, file_id)
            return
    
    # Generate new token
    new_token = secrets.token_urlsafe(16)
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
        f"Token valid for {TOKEN_EXPIRE_HOURS} hours\n\n"
        f"<i>IP: {WHITELIST_IP}</i>",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

# Admin Commands
async def getlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Secure file upload handler"""
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ Admin access required")
        return
    
    try:
        file = update.message.reply_to_message.document
        msg = await context.bot.send_document(
            chat_id=CHANNEL_ID,
            document=file.file_id,
            caption=f"📁 {file.file_name}\n"
                   f"⬆️ Uploaded by @{update.effective_user.username}"
        )
        
        files.insert_one({
            "file_id": file.file_id,
            "message_id": msg.message_id,
            "uploader": update.effective_user.id,
            "timestamp": datetime.now(pytz.utc)
        })
        
        access_url = f"https://t.me/{context.bot.username}?start={file.file_id}"
        await update.message.reply_text(
            f"✅ File stored!\n\n"
            f"<code>{access_url}</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        await update.message.reply_text("⚠️ Failed to store file")

# System Functions
async def maintenance_task():
    """Background tasks"""
    while True:
        try:
            # Clean expired tokens
            result = tokens.delete_many({"expiry": {"$lt": datetime.now(pytz.utc)}})
            if result.deleted_count > 0:
                logger.info(f"Cleaned {result.deleted_count} expired tokens")
            
            # Verify IP every hour
            await verify_ip()
            
            await asyncio.sleep(3600)  # Run hourly
        except Exception as e:
            logger.error(f"Maintenance task failed: {e}")
            await asyncio.sleep(60)

def main():
    # Create application
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .post_init(lambda _: asyncio.create_task(maintenance_task())) \
        .build()
    
    # Handlers
    application.add_handler(CommandHandler("start", verify_token))
    application.add_handler(CommandHandler("getlink", getlink, filters.Document.ALL))
    
    # Error handler
    application.add_error_handler(lambda u, c: logger.error(f"Update {u} caused error {c.error}"))
    
    # Start polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        close_loop=False
    )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        exit(1)
