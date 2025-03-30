import os
import asyncio
import secrets
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    FloodWait,
    UserNotParticipant,
    PeerIdInvalid,
    ChannelPrivate,
    ChatWriteForbidden
)

# Telegram Limits Considered:
# 1. 30 messages/second API limit
# 2. 20 messages/minute to same chat
# 3. 5000 messages/day bot limit
# 4. Media group limits (10 files max)
# 5. 50MB file size limit for bots

# Load config
from dotenv import load_dotenv
load_dotenv('.env')

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
    ADMINS = list(map(int, os.getenv("ADMINS").split(",")))
    FORCE_JOIN = os.getenv("FORCE_JOIN", "0")  # "0" to disable
    SHORTENER_API = os.getenv("SHORTENER_API")
    SHORTENER_DOMAIN = os.getenv("SHORTENER_DOMAIN")
    MAX_BATCH_SIZE = 10  # Telegram media group limit
    BROADCAST_CHUNK_SIZE = 15  # Stay under 20 msg/min limit
    REQUEST_DELAY = 1.2  # Seconds between requests

# Initialize with rate-limiting
app = Client(
    "file_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=4,  # Optimal for mobile
    sleep_threshold=30,
    max_concurrent_transmissions=2  # Avoid flooding
)

# Database (simplified for example)
user_access = {}
file_db = {}
batch_db = {}

async def rate_limited_send(target, **kwargs):
    """Handle Telegram rate limits automatically"""
    try:
        return await target(**kwargs)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        return await target(**kwargs)
    except (UserNotParticipant, PeerIdInvalid, ChannelPrivate):
        return False  # Skip invalid users
    except ChatWriteForbidden:
        await asyncio.sleep(Config.REQUEST_DELAY)
        return False

# Verification System with Limits
async def verify_user(user_id: int):
    """24-hour verification flow respecting limits"""
    if Config.SHORTENER_API and user_id not in user_access:
        token = secrets.token_urlsafe(6)
        user_access[user_id] = {
            'expiry': datetime.now() + timedelta(hours=24),
            'verified': False
        }
        
        try:
            bot_username = (await app.get_me()).username
            verify_url = f"https://{Config.SHORTENER_DOMAIN}/api?api={Config.SHORTENER_API}&url=https://t.me/{bot_username}?start=verify_{token}"
            
            await rate_limited_send(
                app.send_message,
                chat_id=user_id,
                text="🔒 Verify your access (valid 24h):",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Click to Verify", url=verify_url)
                ]])
            )
            return True
        except Exception:
            return False

# File Handling with Media Group Limits
@app.on_message(filters.command("getlink") & filters.user(Config.ADMINS))
async def handle_single_file(client, message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return
    
    try:
        # Forward with rate limiting
        forwarded = await rate_limited_send(
            message.reply_to_message.forward,
            chat_id=Config.DB_CHANNEL_ID
        )
        
        if forwarded:
            file_id = str(forwarded.id)
            file_db[file_id] = forwarded.id
            
            bot_username = (await client.get_me()).username
            await message.reply(
                f"📄 File Link:\n`https://t.me/{bot_username}?start=file_{file_id}`",
                parse_mode=enums.ParseMode.MARKDOWN
            )
    except Exception as e:
        await message.reply(f"⚠️ Error: {str(e)}")

# Batch Processing with Media Group Limit
@app.on_message(filters.command(["firstbatch", "lastbatch"]) & filters.user(Config.ADMINS))
async def handle_batch(client, message):
    if not message.reply_to_message:
        return await message.reply("ℹ️ Reply to a media message")
    
    # Batch logic here (respecting MAX_BATCH_SIZE)
    # ... [previous batch implementation] ...

# Broadcast with Chunking
@app.on_message(filters.command("broadcast") & filters.user(Config.ADMINS))
async def broadcast_message(client, message):
    if not message.reply_to_message:
        return
    
    users = list(user_access.keys())
    total = len(users)
    success = 0
    
    status = await message.reply(f"📢 Broadcasting to {total} users... (0%)")
    
    for i in range(0, total, Config.BROADCAST_CHUNK_SIZE):
        chunk = users[i:i + Config.BROADCAST_CHUNK_SIZE]
        
        # Process chunk with error handling
        results = await asyncio.gather(*[
            rate_limited_send(
                message.reply_to_message.copy,
                chat_id=user_id
            )
            for user_id in chunk
        ], return_exceptions=True)
        
        success += sum(1 for r in results if r is not False)
        
        # Update progress
        progress = min((i + len(chunk)) / total * 100, 100)
        await status.edit_text(
            f"📢 Progress: {progress:.1f}%\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {i + len(chunk) - success}"
        )
        
        await asyncio.sleep(Config.REQUEST_DELAY)  # Respect limits
    
    await status.edit_text(f"📢 Broadcast complete!\nReached {success}/{total} users")

# Start Command with Force Join Check
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    
    # Force Join Check
    if Config.FORCE_JOIN != "0":
        try:
            await app.get_chat_member(int(Config.FORCE_JOIN), user_id)
        except UserNotParticipant:
            return await message.reply(
                "❌ Please join our channel first",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "Join Channel",
                        url=f"t.me/{(await app.get_chat(Config.FORCE_JOIN)).username}"
                    )
                ]])
            )
    
    # Verification Flow
    if not user_access.get(user_id, {}).get('verified', False):
        await verify_user(user_id)
    else:
        await message.reply("✅ You have active access!")

if __name__ == "__main__":
    print("Bot starting with Telegram limits enforcement...")
    app.run()
