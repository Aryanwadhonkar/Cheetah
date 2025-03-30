import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from database import Database
from config import Config

# Initialize
app = Client("CheetahBot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
db = Database(app)

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    user_id = message.from_user.id
    if str(user_id) in Config.ADMINS.split(","):
        await message.reply("👑 **Admin Mode**")
    else:
        await message.reply("🔒 Get a token to access files.")

@app.on_message(filters.command("getlink") & filters.private & filters.user(Config.ADMINS.split(",")))
async def save_file(client: Client, message: Message):
    """Admins only: Store a file and generate link."""
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("❗ Reply to a file.")
        return

    # Save to DB_CHANNEL
    msg = await message.reply_to_message.copy(Config.DB_CHANNEL)
    
    # Log permanently in LOG_CHANNEL
    await db.log_file_link(msg.id, msg.message_id)
    
    # Generate shareable link
    link = f"https://t.me/{client.me.username}?start=file_{msg.id}"
    await message.reply(f"🔗 Permanent Link:\n\n{link}")

@app.on_message(filters.private & filters.regex(r'^/start file_'))
async def send_secured_file(client: Client, message: Message):
    """Send file if user has access."""
    file_id = int(message.text.split("_")[1])
    
    # 1. Check access (SQLite)
    user_id = message.from_user.id
    if not await db.has_access(user_id):  # Implement this in database.py
        await message.reply("❌ Access denied!")
        return
    
    # 2. Fetch from LOG_CHANNEL
    message_id = await db.get_file_message_id(file_id)
    if not message_id:
        await message.reply("❌ File not found!")
        return
    
    # 3. Send file
    await client.copy_message(
        chat_id=user_id,
        from_chat_id=Config.DB_CHANNEL,
        message_id=message_id
    )

if __name__ == "__main__":
    print("🔥 CHEETAH FILE STORE BOT STARTED!")
    app.run()
