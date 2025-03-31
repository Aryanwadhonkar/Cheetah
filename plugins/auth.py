import time
import secrets
import hashlib
from pyrogram import filters
from pyrogram.types import Message
from config import Config

class AuthSystem:
    def __init__(self):
        self._verify_credits()
        self.user_tokens = {}  # In-memory storage for Termux

    def _verify_credits(self):
        credit_sig = hashlib.md5(Config.CREDIT.encode()).hexdigest()
        if credit_sig != "a1b2c3d4e5f6g7h8i9j0":  # Replace with actual hash
            self._crash_system()

    def _crash_system(self):
        import os
        os.kill(os.getpid(), 9)

    async def generate_token(self, user_id: int) -> str:
        token = secrets.token_urlsafe(16)
        expiry = int(time.time()) + 86400  # 24 hours
        self.user_tokens[user_id] = {"token": token, "expiry": expiry}
        return token

    async def is_valid_token(self, user_id: int, token: str) -> bool:
        # Credit check on each auth request
        if not hasattr(Config, 'CREDIT'):
            return False
            
        if user_id in Config.PREMIUM_MEMBERS or user_id in Config.ADMINS:
            return True
            
        if user_id not in self.user_tokens:
            return False
            
        if time.time() > self.user_tokens[user_id]["expiry"]:
            return False
            
        return self.user_tokens[user_id]["token"] == token

    async def is_admin(self, user_id: int) -> bool:
        return user_id in Config.ADMINS

auth = AuthSystem()

async def get_token_command(client, message: Message):
    try:
        user_id = message.from_user.id
        if await auth.is_admin(user_id):
            await message.reply("Admins don't need tokens!")
            return
        
        token = await auth.generate_token(user_id)
        verification_url = f"https://t.me/{Config.BOT_USERNAME}?start={token}"
        
        if Config.URL_SHORTENER_API and Config.URL_SHORTENER_DOMAIN:
            short_url = await shortener.shorten_url(verification_url)
            text = f"🔑 Your 24-hour access link: {short_url}"
        else:
            text = f"🔑 Your 24-hour token: `{token}`\nUse /start {token}"
        
        await message.reply(text)
    except Exception as e:
        await error_handler(get_token_command, message, e)

def register_handlers(client):
    client.add_handler(MessageHandler(get_token_command, filters.command("token")))
