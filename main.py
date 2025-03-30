import os
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery
)
from pyrogram.errors import (
    FloodWait, UserIsBlocked, 
    InputUserDeactivated, PeerIdInvalid
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

# Database (simple JSON file for Termux compatibility)
import json
from pathlib import Path

DB_FILE = Path("filedb.json")

def load_db():
    if not DB_FILE.exists():
        return {"files": {}, "users": {}, "tokens": {}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Helper functions
def generate_token(user_id):
    import secrets
    token = secrets.token_urlsafe(16)
    db = load_db()
    db["tokens"][token] = {
        "user_id": user_id,
        "expires": (datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)).timestamp()
    }
    save_db(db)
    return token

def is_token_valid(token):
    db = load_db()
    token_data = db["tokens"].get(token)
    if not token_data:
        return False
    if datetime.now().timestamp() > token_data["expires"]:
        del db["tokens"][token]
        save_db(db)
        return False
    return True

def shorten_url(url):
    if not SHORTENER_API:
        return url
    try:
        import requests
        response = requests.get(
            f"https://{SHORTENER_DOMAIN}/api?api={SHORTENER_API}&url={url}"
        )
        return response.json().get("shortenedUrl", url)
    except Exception as e:
        logger.error(f"URL shortening failed: {e}")
        return url

# Create Pyrogram client
app = Client(
    "file_store_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=20,
    sleep_threshold=10
)

# Start command
@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    user_id = message.from_user.id
    db = load_db()
    
    if user_id in ADMINS:
        text = "👋 **Admin Panel**\n\n"
        text += "📁 /upload - Upload files to store\n"
        text += "📤 /batch - Upload multiple files at once\n"
        text += "📢 /broadcast - Send message to all users\n"
        text += "🔗 /shortener - Configure URL shortener\n"
        await message.reply(text)
    else:
        if str(user_id) not in db["users"]:
            db["users"][str(user_id)] = {
                "joined": datetime.now().timestamp(),
                "last_active": datetime.now().timestamp()
            }
            save_db(db)
        
        token = generate_token(user_id)
        text = "👋 **Welcome to File Store Bot**\n\n"
        text += "🔑 Your access token:\n"
        text += f"`{token}`\n\n"
        text += f"⚠️ Token expires in {TOKEN_EXPIRE_HOURS} hours\n"
        text += "🔗 Use /token to generate new token after expiration"
        await message.reply(text)

# Token generation
@app.on_message(filters.command("token") & filters.private)
async def new_token(client: Client, message: Message):
    user_id = message.from_user.id
    token = generate_token(user_id)
    text = "🔄 **New Access Token Generated**\n\n"
    text += f"🔑 `{token}`\n\n"
    text += f"⚠️ Expires in {TOKEN_EXPIRE_HOURS} hours"
    await message.reply(text)

# File upload (Admin only)
@app.on_message(filters.command("upload") & filters.private & filters.user(ADMINS))
async def upload_file(client: Client, message: Message):
    await message.reply("📤 Please send the file(s) you want to store")

@app.on_message(filters.private & filters.user(ADMINS) & (filters.document | filters.photo | filters.video | filters.audio))
async def save_file(client: Client, message: Message):
    try:
        # Forward file to DB channel
        forwarded = await message.forward(DB_CHANNEL_ID)
        
        # Save to database
        db = load_db()
        file_id = str(forwarded.id)
        db["files"][file_id] = {
            "message_id": forwarded.id,
            "date": datetime.now().timestamp(),
            "caption": message.caption or "",
            "type": message.media.value if message.media else "document"
        }
        save_db(db)
        
        # Generate access link
        token = generate_token("admin")  # Admin token doesn't expire
        file_url = f"https://t.me/{client.me.username}?start=file_{file_id}_{token}"
        short_url = shorten_url(file_url)
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Share Link", url=short_url)]
        ])
        
        await message.reply("✅ File stored successfully!", reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        await message.reply("❌ Failed to save file. Please try again.")

# Batch upload
@app.on_message(filters.command("batch") & filters.private & filters.user(ADMINS))
async def batch_upload(client: Client, message: Message):
    await message.reply(f"📦 Send up to {MAX_FILES_PER_BATCH} files to store as a batch")

@app.on_message(filters.private & filters.user(ADMINS) & filters.media_group)
async def save_batch(client: Client, message: Message):
    try:
        # Forward all files to DB channel
        file_ids = []
        async for msg in client.get_media_group(message.chat.id, message.id):
            forwarded = await msg.forward(DB_CHANNEL_ID)
            file_ids.append(str(forwarded.id))
            
            # Save to database
            db = load_db()
            db["files"][str(forwarded.id)] = {
                "message_id": forwarded.id,
                "date": datetime.now().timestamp(),
                "caption": msg.caption or "",
                "type": msg.media.value if msg.media else "document",
                "batch": True
            }
            save_db(db)
        
        if not file_ids:
            return await message.reply("❌ No files received")
        
        # Generate batch access link
        token = generate_token("admin")  # Admin token doesn't expire
        batch_url = f"https://t.me/{client.me.username}?start=batch_{'_'.join(file_ids)}_{token}"
        short_url = shorten_url(batch_url)
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Share Batch Link", url=short_url)]
        ])
        
        await message.reply(f"✅ {len(file_ids)} files stored as batch!", reply_markup=buttons)
    except Exception as e:
        logger.error(f"Error saving batch: {e}")
        await message.reply("❌ Failed to save batch. Please try again.")

# File access
@app.on_message(filters.private & filters.regex(r"^/start (file|batch)_"))
async def send_file(client: Client, message: Message):
    try:
        parts = message.text.split("_")
        if len(parts) < 3:
            return await message.reply("❌ Invalid link")
        
        file_type = parts[0].split()[1]
        file_ids = parts[1].split("_")
        token = parts[2]
        
        if not is_token_valid(token):
            return await message.reply("🔒 Token expired or invalid. Use /token to get a new one.")
        
        db = load_db()
        messages = []
        
        for file_id in file_ids:
            if file_id not in db["files"]:
                continue
            
            msg_id = db["files"][file_id]["message_id"]
            try:
                msg = await client.get_messages(DB_CHANNEL_ID, msg_id)
                messages.append(msg)
            except Exception as e:
                logger.error(f"Error retrieving file {file_id}: {e}")
        
        if not messages:
            return await message.reply("❌ Files not found")
        
        # Send files with restricted forwarding
        for msg in messages:
            try:
                await msg.copy(
                    message.chat.id,
                    caption=msg.caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔗 Get New Link", url=f"https://t.me/{client.me.username}?start=token")]
                    ]) if token != "admin" else None
                )
                # Add slight delay to avoid flood
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                logger.error(f"Error sending file: {e}")
        
        # Update user last active
        user_id = message.from_user.id
        if str(user_id) in db["users"]:
            db["users"][str(user_id)]["last_active"] = datetime.now().timestamp()
            save_db(db)
            
    except Exception as e:
        logger.error(f"Error in file access: {e}")
        await message.reply("❌ Failed to retrieve files. Please try again.")

# Broadcast message to all users
@app.on_message(filters.command("broadcast") & filters.private & filters.user(ADMINS))
async def broadcast(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply("ℹ️ Please reply to a message to broadcast")
    
    db = load_db()
    users = db["users"].keys()
    total = len(users)
    success = 0
    failed = 0
    
    status = await message.reply(f"📢 Broadcasting to {total} users...")
    
    for user_id in users:
        try:
            await message.reply_to_message.copy(int(user_id))
            success += 1
            # Update user last active
            db["users"][user_id]["last_active"] = datetime.now().timestamp()
        except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
            failed += 1
            # Remove inactive users
            del db["users"][user_id]
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"Broadcast error for {user_id}: {e}")
            failed += 1
        finally:
            if (success + failed) % 10 == 0:
                await status.edit_text(
                    f"📢 Broadcast progress:\n"
                    f"✅ Success: {success}\n"
                    f"❌ Failed: {failed}\n"
                    f"📊 Total: {total}"
                )
    
    save_db(db)
    await status.edit_text(
        f"📢 Broadcast completed!\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total: {total}"
    )

# URL Shortener configuration
@app.on_message(filters.command("shortener") & filters.private & filters.user(ADMINS))
async def url_shortener(client: Client, message: Message):
    text = "🔗 **URL Shortener Configuration**\n\n"
    text += f"Current API: `{SHORTENER_API or 'Not set'}`\n"
    text += f"Current Domain: `{SHORTENER_DOMAIN or 'Not set'}`\n\n"
    text += "To update, reply with:\n"
    text += "/set_shortener api_key domain.com"
    await message.reply(text)

@app.on_message(filters.command("set_shortener") & filters.private & filters.user(ADMINS))
async def set_shortener(client: Client, message: Message):
    if len(message.command) < 3:
        return await message.reply("ℹ️ Usage: /set_shortener api_key domain.com")
    
    api_key = message.command[1]
    domain = message.command[2]
    
    # Update .env file
    with open(".env", "r") as f:
        lines = f.readlines()
    
    with open(".env", "w") as f:
        for line in lines:
            if line.startswith("SHORTENER_API="):
                f.write(f"SHORTENER_API={api_key}\n")
            elif line.startswith("SHORTENER_DOMAIN="):
                f.write(f"SHORTENER_DOMAIN={domain}\n")
            else:
                f.write(line)
    
    # Reload environment
    load_dotenv(override=True)
    await message.reply("✅ URL shortener configuration updated!")

# Error handling
@app.on_edited_message()
async def edited_message(client: Client, message: Message):
    await message.reply("ℹ️ Editing messages is not supported")

# Start the bot
if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run()
