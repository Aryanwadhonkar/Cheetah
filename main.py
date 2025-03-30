import os
import asyncio
import logging
import sqlite3
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

# Minimal configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load config
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
ADMINS = [int(admin) for admin in os.getenv("ADMINS").split(",")]
BROADCAST_CHUNK_SIZE = int(os.getenv("BROADCAST_CHUNK_SIZE", 20))  # Default chunk size

# Simple SQLite setup
def init_db():
    with sqlite3.connect('filedb.db') as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            last_active REAL
        )''')

init_db()

# Optimized broadcast function
async def broadcast(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply("Reply to a message to broadcast")
        return

    with sqlite3.connect('filedb.db') as conn:
        users = [row[0] for row in conn.execute("SELECT user_id FROM users")]
    
    total = len(users)
    success = 0
    
    status = await message.reply(f"Broadcasting to {total} users...")
    
    for i in range(0, total, BROADCAST_CHUNK_SIZE):
        chunk = users[i:i + BROADCAST_CHUNK_SIZE]
        
        # Process chunk with error handling
        try:
            await asyncio.gather(*[
                send_message(client, message.reply_to_message, user_id)
                for user_id in chunk
            ])
            success += len(chunk)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"Chunk failed: {e}")
        
        # Update progress
        if i % 50 == 0:  # Update every 50 users to reduce load
            await status.edit_text(
                f"Progress: {i + len(chunk)}/{total}\n"
                f"Success: {success}"
            )
    
    await status.edit_text(f"✅ Broadcast complete!\nSent to {success}/{total} users")

async def send_message(client: Client, message: Message, user_id: int):
    try:
        await message.copy(user_id)
        # Lightweight activity update
        with sqlite3.connect('filedb.db') as conn:
            conn.execute(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (datetime.now().timestamp(), user_id)
    except Exception:
        pass  # Silent fail to keep broadcasting

# Pyrogram client with essential settings
app = Client(
    "file_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=10,  # Balanced for performance
    sleep_threshold=30
)

# Command handlers
@app.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast_cmd(client, message):
    await broadcast(client, message)

@app.on_message(filters.command("start"))
async def start(client, message):
    with sqlite3.connect('filedb.db') as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, last_active) VALUES (?, ?)",
            (message.from_user.id, datetime.now().timestamp())
        )
    await message.reply("Bot started!")

if __name__ == "__main__":
    logger.info("Starting optimized bot...")
    app.run()
