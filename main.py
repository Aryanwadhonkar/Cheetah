import os
import asyncio
import secrets
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand
)
from pyrogram.errors import (
    FloodWait,
    UserNotParticipant,
    PeerIdInvalid,
    ChannelPrivate,
    ChatWriteForbidden
)

# Load config
from dotenv import load_dotenv
load_dotenv('.env')

class Config:
    # Required
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
    ADMINS = list(map(int, os.getenv("ADMINS").split(",")))
    
    # Optional
    FORCE_JOIN = os.getenv("FORCE_JOIN", "0")  # "0" to disable
    SHORTENER_API = os.getenv("SHORTENER_API", "")
    SHORTENER_DOMAIN = os.getenv("SHORTENER_DOMAIN", "")
    
    # Limits
    MAX_BATCH_SIZE = 10  # Telegram media group limit
    BROADCAST_CHUNK_SIZE = 15  # Stay under 20 msg/min limit
    REQUEST_DELAY = 1.2  # Seconds between actions

# Initialize with rate-limiting
app = Client(
    "file_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=4,
    sleep_threshold=30,
    max_concurrent_transmissions=2
)

# Database
user_db = {}  # {user_id: expiry_timestamp}
file_db = {}  # {file_id: message_id}
batch_db = {}  # {batch_id: [message_ids]}

async def set_bot_commands():
    await app.set_bot_commands([
        BotCommand("start", "Begin verification"),
        BotCommand("help", "Show commands"),
        BotCommand("status", "Check access time"),
        BotCommand("getlink", "[Admin] Create file link"),
        BotCommand("broadcast", "[Admin] Message all users")
    ])

async def safe_send(target, **kwargs):
    """Handle Telegram limits with retry logic"""
    try:
        return await target(**kwargs)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        return await target(**kwargs)
    except (UserNotParticipant, PeerIdInvalid, ChannelPrivate, ChatWriteForbidden):
        return False

async def verify_user(user_id: int):
    """24-hour verification flow with shortener"""
    if Config.SHORTENER_API:
        token = secrets.token_urlsafe(6)
        user_db[user_id] = datetime.now().timestamp() + 86400  # 24h
        
        bot_username = (await app.get_me()).username
        verify_url = f"https://{Config.SHORTENER_DOMAIN}/api?api={Config.SHORTENER_API}&url=https://t.me/{bot_username}?start=verify_{token}"
        
        await safe_send(
            app.send_message,
            chat_id=user_id,
            text="🔒 Verify your access (valid 24h):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Click to Verify", url=verify_url)
            ]])
        )

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id
    
    # Force join check
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
    
    # Handle verification tokens
    if len(message.command) > 1:
        if message.command[1].startswith("verify_"):
            user_db[user_id] = datetime.now().timestamp() + 86400
            return await message.reply("✅ Verified for 24 hours!")
        elif message.command[1].startswith("file_"):
            file_id = message.command[1].split("_")[1]
            if file_id in file_db:
                await safe_send(
                    app.copy_message,
                    chat_id=message.chat.id,
                    from_chat_id=Config.DB_CHANNEL_ID,
                    message_id=file_db[file_id]
                )
            return
    
    # New user flow
    if user_id not in user_db:
        await verify_user(user_id)
    else:
        expiry = datetime.fromtimestamp(user_db[user_id])
        await message.reply(f"✅ Active until: {expiry.strftime('%Y-%m-%d %H:%M')}")

@app.on_message(filters.command("getlink") & filters.user(Config.ADMINS))
async def getlink_cmd(client, message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.reply("ℹ️ Reply to a file")
    
    forwarded = await safe_send(
        message.reply_to_message.forward,
        chat_id=Config.DB_CHANNEL_ID
    )
    if not forwarded:
        return
    
    file_id = str(forwarded.id)
    file_db[file_id] = forwarded.id
    
    bot_username = (await app.get_me()).username
    await message.reply(
        f"📄 File Link:\n`https://t.me/{bot_username}?start=file_{file_id}`",
        parse_mode=enums.ParseMode.MARKDOWN
    )

@app.on_message(filters.command("broadcast") & filters.user(Config.ADMINS))
async def broadcast_cmd(client, message):
    if not message.reply_to_message:
        return await message.reply("ℹ️ Reply to a message")
    
    users = list(user_db.keys())
    total = len(users)
    success = 0
    
    status = await message.reply(f"📢 Broadcasting to {total} users... (0%)")
    
    for i in range(0, total, Config.BROADCAST_CHUNK_SIZE):
        chunk = users[i:i + Config.BROADCAST_CHUNK_SIZE]
        
        results = await asyncio.gather(*[
            safe_send(
                message.reply_to_message.copy,
                chat_id=user_id
            )
            for user_id in chunk
        ], return_exceptions=True)
        
        success += sum(1 for r in results if r is not False)
        
        progress = min((i + len(chunk)) / total * 100, 100)
        await status.edit_text(
            f"📢 Progress: {progress:.1f}%\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {i + len(chunk) - success}"
        )
        
        await asyncio.sleep(Config.REQUEST_DELAY)
    
    await status.edit_text(f"📢 Complete! Reached {success}/{total} users")

if __name__ == "__main__":
    print("Starting optimized file bot...")
    app.start()
    app.run(set_bot_commands())
