import time
import secrets
from pyrogram import filters
from pyrogram.types import Message
from config import Config
from plugins.utils import error_handler
from plugins.shortener import shorten_url

# Token storage (in-memory for Termux)
user_tokens = {}

async def generate_token(user_id: int) -> str:
    token = secrets.token_urlsafe(16)
    expiry = int(time.time()) + 86400  # 24 hours
    user_tokens[user_id] = {"token": token, "expiry": expiry}
    return token

async def is_valid_token(user_id: int, token: str) -> bool:
    if user_id in Config.PREMIUM_MEMBERS or user_id in Config.ADMINS:
        return True
    if user_id not in user_tokens:
        return False
    if time.time() > user_tokens[user_id]["expiry"]:
        return False
    return user_tokens[user_id]["token"] == token

async def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMINS

def register_handlers(client):
    @client.on_message(filters.command("token"))
    @error_handler
    async def get_token(client, message: Message):
        user_id = message.from_user.id
        if await is_admin(user_id):
            await message.reply("Admins don't need tokens!")
            return
        
        token = await generate_token(user_id)
        verification_url = f"https://t.me/{Config.BOT_USERNAME}?start={token}"
        
        if Config.URL_SHORTENER_API and Config.URL_SHORTENER_DOMAIN:
            short_url = await shorten_url(verification_url)
            text = f"🔑 Your 24-hour access link: {short_url}"
        else:
            text = f"🔑 Your 24-hour token: `{token}`\nUse /start {token}"
        
        await message.reply(text)
