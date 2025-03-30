import os
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
    ChatWriteForbidden
)

# Load config
from dotenv import load_dotenv
load_dotenv('.env')

# Configuration
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
    ADMINS = list(map(int, os.getenv("ADMINS").split(",")))
    FORCE_JOIN = os.getenv("FORCE_JOIN", "0")  # "0" to disable
    SHORTENER_API = os.getenv("SHORTENER_API")
    SHORTENER_DOMAIN = os.getenv("SHORTENER_DOMAIN")

# Initialize bot
app = Client(
    "file_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=4,
    sleep_threshold=30
)

# Database
file_db = {}  # Format: {file_id: message_id}
batch_db = {}  # Format: {batch_id: [message_ids]}
user_access = {}  # Format: {user_id: expiry_timestamp}

# Command menu
commands = [
    BotCommand("start", "Get started"),
    BotCommand("help", "Show commands"),
    BotCommand("getlink", "Generate file link (Admin)"),
    BotCommand("firstbatch", "Start batch upload (Admin)"),
    BotCommand("lastbatch", "Finish batch upload (Admin)"),
    BotCommand("broadcast", "Send announcement (Admin)")
]

# Helper functions
def generate_token():
    return secrets.token_urlsafe(8)

async def check_user(user_id):
    """Check if user has valid access or is in force join channel"""
    if Config.FORCE_JOIN != "0":
        try:
            await app.get_chat_member(int(Config.FORCE_JOIN), user_id)
        except UserNotParticipant:
            return False
    return user_id in user_access and datetime.now().timestamp() < user_access[user_id]

async def send_verification(user_id):
    """Send shortener link for verification"""
    token = generate_token()
    expiry = int((datetime.now() + timedelta(hours=24)).timestamp()
    
    if Config.SHORTENER_API:
        import requests
        try:
            response = requests.get(
                f"https://{Config.SHORTENER_DOMAIN}/api?api={Config.SHORTENER_API}"
                f"&url=https://t.me/{(await app.get_me()).username}?start=verify_{token}"
            )
            return response.json().get("shortenedUrl")
        except:
            pass
    return None

# Command handlers
@app.on_message(filters.command("start"))
async def start(client, message):
    args = message.text.split()
    if len(args) > 1:
        # Handle verification or file access
        if args[1].startswith("verify_"):
            token = args[1].split("_")[1]
            user_access[message.from_user.id] = (datetime.now() + timedelta(hours=24)).timestamp()
            await message.reply("✅ Verified for 24 hours!")
        elif args[1].startswith("file_"):
            file_id = args[1].split("_")[1]
            if file_id in file_db:
                await client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=Config.DB_CHANNEL_ID,
                    message_id=file_db[file_id]
                )
    else:
        if await check_user(message.from_user.id):
            await message.reply("📁 You have active access until: " + 
                datetime.fromtimestamp(user_access[message.from_user.id]).strftime('%Y-%m-%d %H:%M'))
        else:
            verify_link = await send_verification(message.from_user.id)
            if verify_link:
                await message.reply(
                    "🔒 Please verify first:\n" + verify_link,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Verify Now", url=verify_link)]
                    )
                )

@app.on_message(filters.command("getlink") & filters.user(Config.ADMINS))
async def get_link(client, message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.reply("ℹ️ Reply to a file")
    
    forwarded = await message.reply_to_message.forward(Config.DB_CHANNEL_ID)
    file_id = str(forwarded.id)
    file_db[file_id] = forwarded.id
    
    bot_username = (await client.get_me()).username
    await message.reply(
        f"🔗 Permanent File Link:\nhttps://t.me/{bot_username}?start=file_{file_id}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Share Link", url=f"https://t.me/share/url?url=https://t.me/{bot_username}?start=file_{file_id}")]
        )
    )

@app.on_message(filters.command("firstbatch") & filters.user(Config.ADMINS))
async def start_batch(client, message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.reply("ℹ️ Reply to first file")
    
    batch_id = generate_token()
    batch_db[batch_id] = [message.reply_to_message.id]
    await message.reply(f"📦 Batch started! ID: {batch_id}\nNow send /lastbatch when done")

@app.on_message(filters.command("lastbatch") & filters.user(Config.ADMINS))
async def end_batch(client, message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.reply("ℹ️ Reply to last file")
    
    # Get all messages between first and last
    batch_messages = []
    async for msg in client.search_messages(
        chat_id=message.chat.id,
        query="",
        offset_id=message.reply_to_message.id,
        limit=100
    ):
        if msg.id >= batch_db[batch_id][0]:
            batch_messages.append(msg)
        else:
            break
    
    # Forward to channel and store
    file_ids = []
    for msg in reversed(batch_messages):
        forwarded = await msg.forward(Config.DB_CHANNEL_ID)
        file_ids.append(forwarded.id)
    
    batch_db[batch_id] = file_ids
    bot_username = (await client.get_me()).username
    await message.reply(
        f"📦 Batch complete! {len(file_ids)} files\n"
        f"🔗 Share this link:\nhttps://t.me/{bot_username}?start=batch_{batch_id}"
    )

@app.on_message(filters.command("broadcast") & filters.user(Config.ADMINS))
async def broadcast(client, message):
    if not message.reply_to_message:
        return await message.reply("ℹ️ Reply to a message to broadcast")
    
    users = list(user_access.keys())
    for user_id in users:
        try:
            await message.reply_to_message.copy(user_id)
        except Exception:
            continue

# Error handling
@app.on_errors()
async def error_handler(client, error):
    if isinstance(error, FloodWait):
        await asyncio.sleep(error.value)
    elif isinstance(error, UserNotParticipant):
        await message.reply(
            f"❌ Please join @{await app.get_chat(Config.FORCE_JOIN).username} first",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"t.me/{await app.get_chat(Config.FORCE_JOIN).username}")]
            )
        )

# Start bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run()
