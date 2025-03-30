import os
import secrets
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load configuration
load_dotenv('.env')

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
ADMINS = list(map(int, os.getenv("ADMINS").split(",")))

# Initialize bot
app = Client(
    "file_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=3  # Optimal for mobile
)

# Token storage
active_tokens = {}

def generate_token(file_id: str) -> str:
    token = secrets.token_urlsafe(16)
    active_tokens[token] = {
        "file_id": file_id,
        "expiry": datetime.now() + timedelta(hours=24)
    }
    return token

# Command handlers
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply("📁 Send me any file to get a shareable link!")

@app.on_message(filters.media & filters.private & filters.user(ADMINS))
async def handle_media(client, message):
    try:
        # Forward to channel
        forwarded = await message.forward(DB_CHANNEL_ID)
        
        # Generate token
        token = generate_token(str(forwarded.id))
        
        # Create link
        bot_username = (await client.get_me()).username
        link = f"https://t.me/{bot_username}?start=file_{forwarded.id}_{token}"
        
        await message.reply(
            f"🔗 Your 24-hour access link:\n{link}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Share Link", url=link)]
            ])
        )
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.regex(r"^/start file_"))
async def handle_file_request(client, message):
    try:
        _, file_id, token = message.text.split("_")
        
        # Verify token
        if token not in active_tokens:
            return await message.reply("⚠️ Invalid token!")
            
        if datetime.now() > active_tokens[token]["expiry"]:
            del active_tokens[token]
            return await message.reply("⌛ Link expired!")
            
        # Send file
        await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=DB_CHANNEL_ID,
            message_id=int(file_id)
        )
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    print("✅ Bot is starting...")
    app.run()
