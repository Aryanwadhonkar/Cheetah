import os
import time
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid

# Android-specific imports
try:
    import android.thermal as at
    ANDROID_MODE = True
except:
    ANDROID_MODE = False

# Load config
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configs with Android defaults
class Config:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
    ADMINS = [int(admin) for admin in os.getenv("ADMINS").split(",")]
    AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES", 10))
    BROADCAST_CHUNK_SIZE = int(os.getenv("BROADCAST_CHUNK_SIZE", 18 if ANDROID_MODE else 20))
    CHUNK_DELAY = float(os.getenv("CHUNK_DELAY_SECONDS", 0.8 if ANDROID_MODE else 1.0))
    MAX_CONCURRENT_BROADCASTS = int(os.getenv("MAX_CONCURRENT_BROADCASTS", 2 if ANDROID_MODE else 5))
    ANDROID_MODE = ANDROID_MODE

# Database setup
def init_db():
    conn = sqlite3.connect('filedb.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        is_5g_user BOOLEAN DEFAULT 0,
        last_active REAL
    )''')
    conn.commit()
    conn.close()

init_db()

# Thermal management
class AndroidThermal:
    @staticmethod
    async def check_throttle():
        if not Config.ANDROID_MODE:
            return False
        
        try:
            temp = at.current_temp()
            if temp > 45:
                logger.warning(f"Thermal throttling! Current temp: {temp}°C")
                await asyncio.sleep(2)
                return True
        except Exception as e:
            logger.error(f"Thermal check failed: {e}")
        return False

# Optimized broadcast with 5G prioritization
async def smart_broadcast(client, message):
    if not message.reply_to_message:
        await message.reply("ℹ️ Reply to a message to broadcast")
        return

    conn = sqlite3.connect('filedb.db')
    cursor = conn.cursor()
    
    try:
        # Get users with 5G priority
        cursor.execute("SELECT user_id FROM users WHERE is_5g_user = 1")
        users_5g = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT user_id FROM users WHERE is_5g_user = 0")
        users_4g = [row[0] for row in cursor.fetchall()]

        total = len(users_5g) + len(users_4g)
        success = failed = 0

        status = await message.reply(f"📢 Broadcasting to {total} users... (0%)")

        # Process 5G users first
        for i in range(0, len(users_5g), Config.BROADCAST_CHUNK_SIZE):
            chunk = users_5g[i:i + Config.BROADCAST_CHUNK_SIZE]
            results = await asyncio.gather(*[send_chunk(client, message.reply_to_message, user) for user in chunk])
            success += sum(1 for r in results if r)
            failed += sum(1 for r in results if not r)
            
            # Update progress
            progress = (i + len(chunk)) / total * 100
            await status.edit_text(f"📢 5G Users: {progress:.1f}%\n✅ Success: {success}\n❌ Failed: {failed}")
            
            if await AndroidThermal.check_throttle():
                await status.reply("⚠️ Cooling down...")
                await asyncio.sleep(3)

            await asyncio.sleep(Config.CHUNK_DELAY)

        # Then process 4G users
        for i in range(0, len(users_4g), Config.BROADCAST_CHUNK_SIZE):
            chunk = users_4g[i:i + Config.BROADCAST_CHUNK_SIZE]
            results = await asyncio.gather(*[send_chunk(client, message.reply_to_message, user) for user in chunk])
            success += sum(1 for r in results if r)
            failed += sum(1 for r in results if not r)
            
            progress = (len(users_5g) + i + len(chunk)) / total * 100
            await status.edit_text(f"📢 4G Users: {progress:.1f}%\n✅ Success: {success}\n❌ Failed: {failed}")
            
            if await AndroidThermal.check_throttle():
                await status.reply("⚠️ Cooling down...")
                await asyncio.sleep(3)

            await asyncio.sleep(Config.CHUNK_DELAY * 1.5)  # Longer delay for 4G

        await status.edit_text(f"📢 Broadcast Complete!\n5G: {len(users_5g)} users\n4G: {len(users_4g)} users\n✅ Success: {success}\n❌ Failed: {failed}")

    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await message.reply(f"❌ Broadcast failed: {str(e)}")
    finally:
        conn.close()

async def send_chunk(client, message, user_id):
    try:
        await message.copy(user_id)
        
        # Update last active
        conn = sqlite3.connect('filedb.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (datetime.now().timestamp(), user_id)
        )
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error sending to {user_id}: {e}")
        return False

# Create Pyrogram client with Android optimizations
app = Client(
    "file_store_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=4 if Config.ANDROID_MODE else 10,
    sleep_threshold=30,
    max_concurrent_transmissions=2 if Config.ANDROID_MODE else 5,
    in_memory=True
)

# Register handlers
@app.on_message(filters.command("broadcast") & filters.user(Config.ADMINS))
async def broadcast_handler(client, message):
    await smart_broadcast(client, message)

# Android performance management
@app.on_startup()
async def startup():
    if Config.ANDROID_MODE:
        logger.info("Running in Android-optimized mode")
        try:
            os.system("termux-wake-lock")
            os.system("termux-cpu-performance")
        except:
            pass

@app.on_shutdown()
async def shutdown():
    if Config.ANDROID_MODE:
        try:
            os.system("termux-wake-unlock")
            os.system("termux-cpu-idle")
        except:
            pass

if __name__ == "__main__":
    logger.info("Starting Android-optimized bot...")
    app.run()
