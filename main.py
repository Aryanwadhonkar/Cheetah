import os
import secrets
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand
)
from dotenv import load_dotenv

load_dotenv('.env')

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
ADMINS = list(map(int, os.getenv("ADMINS").split(",")))
SHORTENER_API = os.getenv("SHORTENER_API")
SHORTENER_DOMAIN = os.getenv("SHORTENER_DOMAIN")

# Bot setup
app = Client(
    "file_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=3
)

# Database
verified_users = {}
file_tokens = {}

# Command descriptions
commands = [
    BotCommand("start", "Get started with the bot"),
    BotCommand("help", "Show all commands"),
    BotCommand("batch", "Upload multiple files (Admin only)"),
    BotCommand("shorten", "Create shareable link (Admin only)")
]

async def set_bot_commands():
    await app.set_bot_commands(commands)

# Generate monetized link
def generate_link(file_id: str, is_admin: bool = False) -> str:
    token = secrets.token_urlsafe(8)
    expiry = datetime.now() + timedelta(hours=24)
    
    file_tokens[token] = {
        "file_id": file_id,
        "expiry": expiry,
        "verified": False
    }
    
    if is_admin:
        return f"https://t.me/{(await app.get_me()).username}?start=file_{file_id}_{token}"
    
    if SHORTENER_API and SHORTENER_DOMAIN:
        import requests
        try:
            response = requests.get(
                f"https://{SHORTENER_DOMAIN}/api?api={SHORTENER_API}&url=https://t.me/{(await app.get_me()).username}?start=file_{file_id}_{token}"
            )
            return response.json().get("shortenedUrl")
        except:
            pass
    return None

# Start handler
@app.on_message(filters.command("start"))
async def start(client, message):
    if len(message.command) > 1:
        # Handle file tokens
        _, file_id, token = message.text.split('_')
        if token in file_tokens:
            if not file_tokens[token]["verified"]:
                file_tokens[token]["verified"] = True
                await message.reply("✅ Verification complete! You can now access the file.")
            await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=DB_CHANNEL_ID,
                message_id=int(file_id)
        else:
            await message.reply("⚠️ Invalid or expired token")
    else:
        await message.reply(
            "📁 **File Sharing Bot**\n\n"
            "Admins can upload files and generate shareable links\n"
            "Users must verify through 24-hour links",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆘 Help", callback_data="help")]
            )
        )

# Admin commands
@app.on_message(filters.command("shorten") & filters.user(ADMINS))
async def shorten_file(client, message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.reply("ℹ️ Reply to a file to generate link")
    
    forwarded = await message.reply_to_message.forward(DB_CHANNEL_ID)
    link = await generate_link(str(forwarded.id))
    
    if link:
        await message.reply(
            f"🔗 24-Hour Shareable Link:\n{link}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Share", url=link)]
            )
        )
    else:
        await message.reply("❌ Failed to generate link")

@app.on_message(filters.command("batch") & filters.user(ADMINS))
async def batch_upload(client, message):
    # Implement batch upload logic here
    await message.reply("🛠️ Batch upload feature coming soon!")

# Help command
@app.on_callback_query(filters.regex("help"))
async def show_help(client, callback):
    help_text = """
📚 **Available Commands:**

👨‍💻 *Admin Commands:*
/shorten - Generate shareable link (reply to file)
/batch - Upload multiple files (coming soon)

👤 *User Commands:*
/start - Basic information
/help - Show this message

🔗 *Access Files:*
Use admin-generated links (expire in 24h)
    """
    await callback.message.edit_text(help_text)

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run()
