import os
import time
import logging
import asyncio
import sqlite3
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    FloodWait,
    PeerIdInvalid,
    UserIsBlocked,
    ChatWriteForbidden,
    InputUserDeactivated,
    UserNotParticipant
)

# ASCII Art
CHEETAH_ART = """
   ____ _   _ _____ _____ _   _ _____ _     
  / ___| | | | ____| ____| | | |_   _| |    
 | |   | |_| |  _| |  _| | |_| | | | | |    
 | |___|  _  | |___| |___|  _  | | | | |___ 
  \____|_| |_|_____|_____|_| |_| |_| |_____|
"""

print(CHEETAH_ART)

# Configuration
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "abcdef123456"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"))
ADMINS = [int(admin) for admin in os.getenv("ADMINS", "123456789").split(",")]
DB_CHANNEL = int(os.getenv("DB_CHANNEL", "-1001234567890"))
TOKEN_EXPIRE_HOURS = 24
URL_SHORTENER_API = os.getenv("URL_SHORTENER_API", "")
URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN", "")
FORCE_SUB = os.getenv("FORCE_SUB", "0")  # 0 or channel ID
AUTO_DELETE = int(os.getenv("AUTO_DELETE", "0"))  # 0 or minutes

# Initialize the bot
app = Client(
    "FileStoreBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Database setup
conn = sqlite3.connect('file_store.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS files (
    file_id TEXT PRIMARY KEY,
    file_name TEXT,
    file_type TEXT,
    file_size INTEGER,
    message_id INTEGER,
    date_added TIMESTAMP,
    admin_id INTEGER,
    delete_at TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS batches (
    batch_id TEXT PRIMARY KEY,
    file_ids TEXT,
    date_added TIMESTAMP,
    admin_id INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    token TEXT,
    token_expiry TIMESTAMP,
    date_joined TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS admins (
    admin_id INTEGER PRIMARY KEY
)
''')

# Insert admins
for admin in ADMINS:
    cursor.execute('INSERT OR IGNORE INTO admins (admin_id) VALUES (?)', (admin,))
conn.commit()

# Helper functions
def generate_token(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def is_admin(user_id: int) -> bool:
    cursor.execute('SELECT 1 FROM admins WHERE admin_id = ?', (user_id,))
    return cursor.fetchone() is not None

def get_user_token(user_id: int) -> Optional[str]:
    cursor.execute('SELECT token, token_expiry FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        token, expiry = result
        if datetime.fromisoformat(expiry) > datetime.now():
            return token
    return None

def update_user_token(user_id: int, username: str, first_name: str, last_name: str) -> str:
    token = generate_token()
    expiry = datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    
    cursor.execute('''
    INSERT INTO users (user_id, username, first_name, last_name, token, token_expiry, date_joined)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        username = excluded.username,
        first_name = excluded.first_name,
        last_name = excluded.last_name,
        token = excluded.token,
        token_expiry = excluded.token_expiry
    ''', (user_id, username, first_name, last_name, token, expiry.isoformat(), datetime.now().isoformat()))
    conn.commit()
    return token

def save_file(file_id: str, file_name: str, file_type: str, file_size: int, message_id: int, admin_id: int):
    delete_at = None
    if AUTO_DELETE > 0:
        delete_at = (datetime.now() + timedelta(minutes=AUTO_DELETE)).isoformat()
    
    cursor.execute('''
    INSERT INTO files (file_id, file_name, file_type, file_size, message_id, date_added, admin_id, delete_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (file_id, file_name, file_type, file_size, message_id, datetime.now().isoformat(), admin_id, delete_at))
    conn.commit()

def save_batch(batch_id: str, file_ids: List[str], admin_id: int):
    cursor.execute('''
    INSERT INTO batches (batch_id, file_ids, date_added, admin_id)
    VALUES (?, ?, ?, ?)
    ''', (batch_id, ','.join(file_ids), datetime.now().isoformat(), admin_id))
    conn.commit()

def get_file(file_id: str):
    cursor.execute('SELECT * FROM files WHERE file_id = ?', (file_id,))
    return cursor.fetchone()

def get_batch(batch_id: str):
    cursor.execute('SELECT * FROM batches WHERE batch_id = ?', (batch_id,))
    return cursor.fetchone()

def short_url(long_url: str) -> str:
    if not URL_SHORTENER_API or not URL_SHORTENER_DOMAIN:
        return long_url
    
    # Implement your URL shortener API call here
    # Example: requests.post(URL_SHORTENER_API, json={"url": long_url})
    # Return shortened URL
    
    return f"{URL_SHORTENER_DOMAIN}/" + long_url.split('/')[-1]

async def send_log(message: str):
    try:
        await app.send_message(DB_CHANNEL, message)
    except Exception as e:
        logging.error(f"Error sending log: {e}")

async def check_user_subscribed(user_id: int) -> bool:
    if FORCE_SUB == "0":
        return True
    
    try:
        channel_id = int(FORCE_SUB)
        member = await app.get_chat_member(channel_id, user_id)
        return member.status not in ["left", "kicked"]
    except UserNotParticipant:
        return False
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return True  # Assume subscribed to avoid blocking due to errors

async def auto_delete_expired_files():
    while True:
        try:
            now = datetime.now().isoformat()
            cursor.execute('SELECT file_id, message_id FROM files WHERE delete_at IS NOT NULL AND delete_at < ?', (now,))
            expired_files = cursor.fetchall()
            
            for file_id, message_id in expired_files:
                try:
                    # Delete from DB channel
                    await app.delete_messages(DB_CHANNEL, message_id)
                    
                    # Delete from database
                    cursor.execute('DELETE FROM files WHERE file_id = ?', (file_id,))
                    conn.commit()
                    
                    logging.info(f"Auto-deleted file {file_id}")
                except Exception as e:
                    logging.error(f"Error deleting file {file_id}: {e}")
            
            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logging.error(f"Error in auto_delete_expired_files: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error

# Start auto-delete task if enabled
if AUTO_DELETE > 0:
    asyncio.create_task(auto_delete_expired_files())

# Command handlers
@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    # Check force subscription
    if FORCE_SUB != "0" and not is_admin(user_id):
        subscribed = await check_user_subscribed(user_id)
        if not subscribed:
            channel_id = int(FORCE_SUB)
            try:
                channel = await client.get_chat(channel_id)
                invite_link = await channel.export_invite_link()
                await message.reply_text(
                    f"⚠️ Please join our channel first!\n\n"
                    f"Join: {channel.title}\n"
                    f"Then try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Join Channel", url=invite_link),
                        InlineKeyboardButton("Try Again", url=f"https://t.me/{client.me.username}?start=start")
                    ]])
                )
                return
            except Exception as e:
                await message.reply_text(f"Error checking channel subscription: {e}")
                return
    
    if is_admin(user_id):
        await message.reply_text(
            "👋 **Admin Welcome!**\n\n"
            "You can use the following commands:\n"
            "/getlink - Store a single file and get link\n"
            "/firstbatch - Start a batch upload\n"
            "/lastbatch - Finish batch upload and get link\n"
            "/broadcast - Send message to all users\n"
            "/stats - Get bot statistics"
        )
    else:
        token = get_user_token(user_id)
        if token:
            await message.reply_text(
                f"👋 Welcome back!\n\n"
                f"Your token is valid until: {datetime.fromisoformat(cursor.execute('SELECT token_expiry FROM users WHERE user_id = ?', (user_id,)).fetchone()[0]}\n\n"
                f"Use the links provided by admins to access files."
            )
        else:
            await message.reply_text(
                "👋 Welcome!\n\n"
                "To access files, you need to get a token by completing the verification process.\n\n"
                "Please visit our 24-hour link to get your access token."
            )

# [Previous command handlers remain the same, just add force sub check to handle_file_access]

@app.on_message(filters.private & filters.text & filters.regex(r'^/start [a-zA-Z0-9]+$'))
async def handle_file_access(client: Client, message: Message):
    user_id = message.from_user.id
    access_id = message.text.split()[1]
    
    # Check force subscription
    if FORCE_SUB != "0" and not is_admin(user_id):
        subscribed = await check_user_subscribed(user_id)
        if not subscribed:
            channel_id = int(FORCE_SUB)
            try:
                channel = await client.get_chat(channel_id)
                invite_link = await channel.export_invite_link()
                await message.reply_text(
                    f"⚠️ Please join our channel first!\n\n"
                    f"Join: {channel.title}\n"
                    f"Then try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Join Channel", url=invite_link),
                        InlineKeyboardButton("Try Again", url=f"https://t.me/{client.me.username}?start={access_id}")
                    ]])
                )
                return
            except Exception as e:
                await message.reply_text(f"Error checking channel subscription: {e}")
                return
    
    # [Rest of the handle_file_access function remains the same]
    # Check if user has valid token (except admins)
    if not is_admin(user_id):
        token = get_user_token(user_id)
        if not token:
            await message.reply_text(
                "🔒 Access Denied\n\n"
                "You need a valid token to access files. Please complete the verification process first."
            )
            return
    
    try:
        # Check if it's a single file
        file_data = get_file(access_id)
        if file_data:
            _, file_name, _, _, message_id, _, _, _ = file_data
            await client.copy_message(
                chat_id=user_id,
                from_chat_id=DB_CHANNEL,
                message_id=message_id,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔗 Get New Token", url="YOUR_24H_LINK_HERE")
                ]]) if not is_admin(user_id) else None
            )
            return
        
        # Check if it's a batch
        batch_data = get_batch(access_id)
        if batch_data:
            _, file_ids_str, _, _ = batch_data
            file_ids = file_ids_str.split(',')
            
            for file_id in file_ids:
                file_data = get_file(file_id)
                if file_data:
                    _, _, _, _, message_id, _, _, _ = file_data
                    await client.copy_message(
                        chat_id=user_id,
                        from_chat_id=DB_CHANNEL,
                        message_id=message_id
                    )
                    await asyncio.sleep(0.5)  # Avoid flood
            
            if not is_admin(user_id):
                await message.reply_text(
                    "✅ All files sent!\n\n"
                    "Remember to get a new token when this one expires.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔗 Get New Token", url="YOUR_24H_LINK_HERE")
                    ]])
                )
            return
        
        await message.reply_text("❌ Invalid access ID. The file or batch may have been deleted.")
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await handle_file_access(client, message)
    except Exception as e:
        await message.reply_text(f"❌ Error accessing file: {str(e)}")
        logging.error(f"Error in handle_file_access: {e}")

# [Rest of the code remains the same]
