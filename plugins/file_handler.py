import time
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from plugins.utils import error_handler
from plugins.auth import is_valid_token, is_admin
from plugins.database import store_file, get_file

def register_handlers(client):
    @client.on_message(filters.command("getlink") & filters.private)
    @error_handler
    async def get_single_link(client, message: Message):
        if not await is_admin(message.from_user.id):
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

    @client.on_message(filters.command(["firstbatch", "lastbatch"]) & filters.private)
    @error_handler
    async def batch_links(client, message: Message):
        # Implementation for batch file handling
        pass

    @client.on_message(filters.command("start") & filters.regex(r"^file_"))
    @error_handler
    async def send_file(client, message: Message):
        # Extract file ID and token
        parts = message.text.split("_")
        if len(parts) < 2:
            await message.reply("Invalid link!")
            return
        
        file_id = parts[1]
        token = parts[2] if len(parts) > 2 else None
        
        # Verify access
        if not await is_valid_token(message.from_user.id, token):
            await message.reply("Token expired or invalid! Get a new one with /token")
            return
        
        # Retrieve and send file
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
        
        # Auto-delete if enabled
        if Config.AUTO_DELETE:
            await asyncio.sleep(Config.AUTO_DELETE * 60)
            await sent_msg.delete()
