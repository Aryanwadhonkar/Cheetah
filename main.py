import os
import hashlib
import secrets
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Configuration
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
ADMINS = [int(admin) for admin in os.getenv("ADMINS").split(",")]
SHORTENER_API = os.getenv("SHORTENER_API")  # Your shortener API key
SHORTENER_DOMAIN = os.getenv("SHORTENER_DOMAIN")  # e.g. "example.com"
TOKEN_EXPIRE_HOURS = 24

# In-memory token storage (replace with DB in production)
active_tokens = {}

def generate_shortlink(file_id: str) -> str:
    """Generate monetized shortlink with 24h token"""
    token = secrets.token_urlsafe(16)
    expiry = datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    
    # Store token
    active_tokens[token] = {
        "file_id": file_id,
        "expiry": expiry
    }
    
    # Generate shortlink
    base_url = f"https://t.me/{Client.me.username}?start=file_{file_id}_{token}"
    
    if SHORTENER_API and SHORTENER_DOMAIN:
        import requests
        try:
            response = requests.get(
                f"https://{SHORTENER_DOMAIN}/api?api={SHORTENER_API}&url={base_url}"
            )
            return response.json().get("shortenedUrl", base_url)
        except:
            return base_url
    return base_url

@app.on_message(filters.command("shorten") & filters.private)
async def shorten_command(client: Client, message: Message):
    """Generate a monetized shortlink"""
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("Reply to a media file to generate shortlink")
        return
    
    # Forward file to DB channel
    forwarded = await message.reply_to_message.forward(DB_CHANNEL_ID)
    file_id = str(forwarded.id)
    
    # Generate shortlink
    shortlink = generate_shortlink(file_id)
    
    await message.reply(
        f"🔗 Monetized Shortlink (24h):\n{shortlink}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Earn Now", url=shortlink)]
        ])
    )

@app.on_message(filters.regex(r"^/start file_") & filters.private)
async def handle_token_access(client: Client, message: Message):
    """Verify token and grant access"""
    _, file_id, token = message.text.split("_")
    
    # Token validation
    if token not in active_tokens:
        await message.reply("❌ Invalid or expired token")
        return
    
    if datetime.now() > active_tokens[token]["expiry"]:
        await message.reply("⌛ Token expired")
        del active_tokens[token]
        return
    
    # Send file
    try:
        msg = await client.get_messages(DB_CHANNEL_ID, int(file_id))
        await msg.copy(
            message.chat.id,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Get New Token", callback_data="new_token")]
            ])
        )
    except Exception as e:
        await message.reply("❌ File access failed")

# Callback for new tokens
@app.on_callback_query(filters.regex("new_token"))
async def new_token_callback(client, callback_query):
    """Generate new monetized token"""
    shortlink = generate_shortlink(callback_query.message.reply_to_message.id)
    await callback_query.message.edit_text(
        f"🔗 New Monetized Link (24h):\n{shortlink}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Earn Again", url=shortlink)]
        ])
    )
