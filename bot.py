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

# Constants using your .env values
TOKEN = "8065030018:AAHfT1hUGXg9kF64HCWotf7GLR-J77KEKAo"
ADMINS = [1672634667]
CHANNEL_ID = -1002348593955
FORCE_SUB = "0"  # Force sub disabled
AUTO_DELETE_TIME = 0  # Auto-delete disabled
MONGO_URL = "mongodb+srv://Wleakshere:Thunderstrikes27@wleakshere.api7w.mongodb.net/?retryWrites=true&w=majority&appName=Wleakshere"

# MongoDB setup with your specified database name
client = MongoClient(
    MONGO_URL,
    tls=True,  # Enable TLS/SSL
    tlsAllowInvalidCertificates=True,  # Only for testing, remove in production
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
    serverSelectionTimeoutMS=30000
)
db = client.get_database("wleakfiles")  # Using your specified database name

# Collections setup with proper indexes
users = db.users
tokens = db.tokens
file_links = db.file_links

# Create indexes
users.create_indexes([
    IndexModel([("user_id", 1)], unique=True),
    IndexModel([("is_premium", 1)]),
    IndexModel([("is_banned", 1)])
])

tokens.create_indexes([
    IndexModel([("user_id", 1), ("token", 1)], unique=True),
    IndexModel([("expiry", 1)], expireAfterSeconds=0)  # Auto-delete expired tokens
])

file_links.create_index([("file_id", 1)])

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
    user = users.find_one({"user_id": user_id})
    return user.get("is_premium", False) if user else False

async def is_banned(user_id: int) -> bool:
    user = users.find_one({"user_id": user_id})
    return user.get("is_banned", False) if user else False

async def update_user_info(user_id: int, username: str, first_name: str, last_name: str):
    users.update_one(
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
    
    tokens.insert_one({
        "user_id": user_id,
        "token": token,
        "expiry": expiry
    })
    return token

async def validate_token(user_id: int, token: str) -> bool:
    return tokens.count_documents({
        "user_id": user_id,
        "token": token,
        "expiry": {"$gt": datetime.now(pytz.utc)}
    }) > 0

async def store_file_link(file_id: str, short_url: str):
    file_links.insert_one({
        "file_id": file_id,
        "short_url": short_url,
        "created_at": datetime.now(pytz.utc)
    })

async def get_file_link(file_id: str) -> Optional[str]:
    link = file_links.find_one({"file_id": file_id})
    return link.get("short_url") if link else None

# ... [Rest of your command handlers and main function remain the same]
# Just replace all database operations with the new collection names:
# - files_collection → file_links
# - users_collection → users
# - tokens_collection → tokens

def main():
    try:
        # Verify MongoDB connection
        client.server_info()
        logger.info("Connected to MongoDB 'wleakfiles' database successfully")
        
        # Create application
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", handle_deep_link))
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
