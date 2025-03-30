import os
import time
import logging
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery
)
from pyrogram.errors import (
    FloodWait, UserIsBlocked, 
    InputUserDeactivated, PeerIdInvalid,
    ChannelPrivate, ChatWriteForbidden
)

# Load config
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configs
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
ADMINS = [int(admin) for admin in os.getenv("ADMINS").split(",")]
SHORTENER_API = os.getenv("SHORTENER_API")
SHORTENER_DOMAIN = os.getenv("SHORTENER_DOMAIN")
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", 24))
MAX_FILES_PER_BATCH = int(os.getenv("MAX_FILES_PER_BATCH", 10))
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES", 10))
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", 5))
BROADCAST_CHUNK_SIZE = int(os.getenv("BROADCAST_CHUNK_SIZE", 20))

# Database setup
import json
from pathlib import Path
import sqlite3  # Switching to SQLite for better performance

DB_FILE = Path("filedb.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        file_id TEXT PRIMARY KEY,
        message_id INTEGER,
        date REAL,
        caption TEXT,
        type TEXT,
        batch INTEGER DEFAULT 0
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        joined REAL,
        last_active REAL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tokens (
        token TEXT PRIMARY KEY,
        user_id TEXT,
        expires REAL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scheduled_deletes (
        chat_id INTEGER,
        message_id INTEGER,
        delete_time REAL,
        PRIMARY KEY(chat_id, message_id)
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Connection pool for database
def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# Helper functions with connection management
def generate_token(user_id):
    import secrets
    token = secrets.token_urlsafe(16)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT OR REPLACE INTO tokens (token, user_id, expires) VALUES (?, ?, ?)',
        (token, str(user_id), (datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)).timestamp())
    )
    
    conn.commit()
    conn.close()
    return token

def is_token_valid(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT user_id, expires FROM tokens WHERE token = ?',
        (token,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False
    
    user_id, expires = result
    if datetime.now().timestamp() > expires:
        delete_token(token)
        return False
    
    return True

def delete_token(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tokens WHERE token = ?', (token,))
    conn.commit()
    conn.close()

def shorten_url(url):
    if not SHORTENER_API:
        return url
    try:
        import requests
        response = requests.get(
            f"https://{SHORTENER_DOMAIN}/api?api={SHORTENER_API}&url={url}",
            timeout=5
        )
        return response.json().get("shortenedUrl", url)
    except Exception as e:
        logger.error(f"URL shortening failed: {e}")
        return url

# Auto-delete scheduler
async def auto_delete_scheduler(client):
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get messages due for deletion
            cursor.execute(
                'SELECT chat_id, message_id FROM scheduled_deletes WHERE delete_time <= ?',
                (datetime.now().timestamp(),)
            )
            messages = cursor.fetchall()
            
            # Delete them
            for chat_id, message_id in messages:
                try:
                    await client.delete_messages(chat_id, message_id)
                    cursor.execute(
                        'DELETE FROM scheduled_deletes WHERE chat_id = ? AND message_id = ?',
                        (chat_id, message_id)
                    )
                except Exception as e:
                    logger.error(f"Failed to delete message {message_id} in chat {chat_id}: {e}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error in auto-delete scheduler: {e}")
        
        # Check every minute
        await asyncio.sleep(60)

# Rate limiter
class RateLimiter:
    def __init__(self, max_calls, time_frame):
        self.max_calls = max_calls
        self.time_frame = time_frame
        self.calls = []
    
    async def __aenter__(self):
        now = time.time()
        # Remove calls outside time frame
        self.calls = [call for call in self.calls if call > now - self.time_frame]
        
        if len(self.calls) >= self.max_calls:
            wait_time = self.time_frame - (now - self.calls[0])
            await asyncio.sleep(wait_time)
            return False
        
        self.calls.append(now)
        return True
    
    async def __aexit__(self, exc_type, exc, tb):
        pass

# Global rate limiter
download_limiter = RateLimiter(MAX_CONCURRENT_DOWNLOADS, 1)  # Max X downloads per second

# Create Pyrogram client with optimized settings
app = Client(
    "file_store_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=100,  # Increased workers
    sleep_threshold=30,  # Higher sleep threshold
    max_concurrent_transmissions=10,  # Limit concurrent uploads/downloads
    in_memory=True  # Reduce disk I/O
)

# Start auto-delete scheduler when bot starts
@app.on_startup()
async def startup(client):
    asyncio.create_task(auto_delete_scheduler(client))

# Start command with rate limiting
@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    async with download_limiter:
        user_id = message.from_user.id
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if user_id in ADMINS:
                text = "👋 **Admin Panel**\n\n"
                text += "📁 /upload - Upload files to store\n"
                text += "📤 /batch - Upload multiple files at once\n"
                text += "📢 /broadcast - Send message to all users\n"
                text += "🔗 /shortener - Configure URL shortener\n"
                await message.reply(text)
            else:
                cursor.execute(
                    'INSERT OR IGNORE INTO users (user_id, joined, last_active) VALUES (?, ?, ?)',
                    (str(user_id), datetime.now().timestamp(), datetime.now().timestamp())
                )
                
                token = generate_token(user_id)
                text = "👋 **Welcome to File Store Bot**\n\n"
                text += "🔑 Your access token:\n"
                text += f"`{token}`\n\n"
                text += f"⚠️ Token expires in {TOKEN_EXPIRE_HOURS} hours\n"
                text += "🔗 Use /token to generate new token after expiration"
                
                await message.reply(text)
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.reply("❌ An error occurred. Please try again.")
        finally:
            conn.close()

# File access with auto-delete
@app.on_message(filters.private & filters.regex(r"^/start (file|batch)_"))
async def send_file(client: Client, message: Message):
    async with download_limiter:
        try:
            parts = message.text.split("_")
            if len(parts) < 3:
                return await message.reply("
