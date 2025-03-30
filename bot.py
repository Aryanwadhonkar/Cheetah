import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytz
from dotenv import load_dotenv
from telegram import (
    Update,
    Chat,
    ChatPermissions,
    Message,
    InputMediaDocument,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ChatAction, ChatMemberStatus, ChatType
from telegram.error import (
    TelegramError,
    BadRequest,
    Forbidden,
    NetworkError,
    RetryAfter,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from pymongo import MongoClient, IndexModel
from pymongo.errors import PyMongoError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
TOKEN = os.getenv("BOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS").split(",")))
CHANNEL_ID = os.getenv("CHANNEL_ID")
FORCE_SUB = os.getenv("FORCE_SUB", "0")
AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", 0))  # in minutes
MONGO_URL = os.getenv("MONGO_URL")

# MongoDB setup with TTL and optimized collections
client = MongoClient(MONGO_URL)
db = client.get_database("file_store_bot")

# Users collection
users_collection = db["users"]
users_collection.create_indexes([
    IndexModel([("user_id", 1)], unique=True),
    IndexModel([("is_premium", 1)]),
    IndexModel([("is_banned", 1)])
])

# Tokens collection with TTL (24 hours)
tokens_collection = db["tokens"]
tokens_collection.create_indexes([
    IndexModel([("user_id", 1), ("token", 1)], unique=True),
    IndexModel([("expiry", 1)], expireAfterSeconds=0)  # Auto-delete expired tokens
])

# File links collection
file_links_collection = db["file_links"]
file_links_collection.create_index([("file_id", 1)])

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

# Helper functions
async def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

async def is_premium(user_id: int) -> bool:
    user = users_collection.find_one({"user_id": user_id})
    return user.get("is_premium", False) if user else False

async def is_banned(user_id: int) -> bool:
    user = users_collection.find_one({"user_id": user_id})
    return user.get("is_banned", False) if user else False

async def update_user_info(user_id: int, username: str, first_name: str, last_name: str):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "last_interaction": datetime.now(pytz.utc)
        }},
        upsert=True
    )

async def generate_token(user_id: int) -> str:
    import secrets
    token = secrets.token_urlsafe(16)
    expiry = datetime.now(pytz.utc) + timedelta(hours=24)
    
    tokens_collection.insert_one({
        "user_id": user_id,
        "token": token,
        "expiry": expiry
    })
    return token

async def validate_token(user_id: int, token: str) -> bool:
    return tokens_collection.count_documents({
        "user_id": user_id,
        "token": token,
        "expiry": {"$gt": datetime.now(pytz.utc)}
    }) > 0

async def store_file_link(file_id: str, short_url: str):
    file_links_collection.insert_one({
        "file_id": file_id,
        "short_url": short_url,
        "created_at": datetime.now(pytz.utc)
    })

async def get_file_link(file_id: str) -> Optional[str]:
    link = file_links_collection.find_one({"file_id": file_id})
    return link.get("short_url") if link else None

async def cleanup_temp_data():
    """Clean up temporary data from context and other sources"""
    # MongoDB TTL indexes handle token expiration automatically
    pass

# Command handlers (optimized for minimal storage)
async def getlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can use this command.")
        return
    
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("Please reply to a file with this command.")
        return
    
    try:
        file = update.message.reply_to_message.document
        file_id = file.file_id
        
        # Store file in channel (no MongoDB storage for files)
        message = await context.bot.send_document(
            chat_id=CHANNEL_ID,
            document=file_id,
            caption=f"File: {file.file_name}\nSize: {file.file_size} bytes",
            disable_notification=True
        )
        
        # Generate access link
        bot_username = context.bot.username
        deep_link = f"https://t.me/{bot_username}?start={file_id}"
        short_url = deep_link  # Remove URL shortener for minimalism
        
        await store_file_link(file_id, short_url)
        
        await update.message.reply_text(
            f"File stored successfully!\n\n"
            f"Access link: {short_url}\n"
            f"File ID: `{file_id}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in getlink: {e}")
        await update.message.reply_text("Failed to store file. Please try again.")

async def handle_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update_user_info(user.id, user.username, user.first_name, user.last_name)
    
    if await is_banned(user.id):
        await update.message.reply_text("You are banned from using this bot.")
        return
    
    file_id = context.args[0] if context.args else None
    if not file_id:
        await start(update, context)
        return
    
    # Check access rights
    if not (await is_admin(user.id) or await is_premium(user.id)):
        if not await validate_token(user.id, context.args[1] if len(context.args) > 1 else ""):
            token = await generate_token(user.id)
            await update.message.reply_text(
                f"You need a valid token to access files. Here's your new token:\n\n"
                f"`{token}`\n\n"
                "Click the link again with this token.",
                parse_mode="Markdown"
            )
            return
    
    # Send the file directly from Telegram's servers
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        
        sent_message = await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_id,
            protect_content=True
        )
        
        if AUTO_DELETE_TIME > 0:
            await asyncio.sleep(AUTO_DELETE_TIME * 60)
            try:
                await sent_message.delete()
            except Exception as e:
                logger.error(f"Failed to auto-delete message: {e}")
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await update.message.reply_text("Failed to send file. Please try again.")
    finally:
        await cleanup_temp_data()

# ... (other handlers optimized similarly)

def main():
    try:
        # Verify MongoDB connection
        client.server_info()
        logger.info("MongoDB connected successfully")
        
        # Create application
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", handle_deep_link))
        application.add_handler(CommandHandler("getlink", getlink))
        # ... (add other handlers)
        
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
