import os
import asyncio
import secrets
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    CallbackQuery
)
from pyrogram.errors import (
    FloodWait,
    UserNotParticipant,
    PeerIdInvalid,
    ChannelPrivate,
    ChatWriteForbidden
)

# ================= CREDIT ENFORCEMENT =================
REQUIRED_CREDITS = [
    "# =============================================",
    "# Original Developer: @wleaksOwner (Telegram)",
    "# GitHub: Aryanwadhonkar (https://github.com/Aryanwadhonkar/Cheetah)",
    "# Removing these credits violates the license!",
    "# ============================================="
]

def validate_credits():
    """Ensure credits exist in this file"""
    with open(__file__, 'r', encoding='utf-8') as f:
        content = f.read()
        missing = [credit for credit in REQUIRED_CREDITS if credit not in content]
        if missing:
            print("CREDIT VIOLATION DETECTED! Missing:")
            print("\n".join(missing))
            print("Bot will not start without proper attribution")
            os._exit(1)

validate_credits()  # Immediate check on import

# ================= CONFIGURATION =================
from dotenv import load_dotenv
load_dotenv('.env')

class Config:
    # Required
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))
    ADMINS = list(map(int, os.getenv("ADMINS").split(",")))
    
    # Optional
    FORCE_JOIN = os.getenv("FORCE_JOIN", "0")
    SHORTENER_API = os.getenv("SHORTENER_API", "")
    SHORTENER_DOMAIN = os.getenv("SHORTENER_DOMAIN", "")
    
    # Limits
    MAX_BATCH_SIZE = 10
    BROADCAST_CHUNK_SIZE = 15
    REQUEST_DELAY = 1.2

# ================= BOT INITIALIZATION =================
app = Client(
    name="CheetahFileBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=4,
    sleep_threshold=30,
    max_concurrent_transmissions=2
)

# ================= DATABASES =================
user_db = {}  # {user_id: expiry_timestamp}
file_db = {}  # {file_id: message_id}
batch_db = {}  # {batch_id: [message_ids]}

# ================= COMMAND SETUP =================
async def set_bot_commands():
    await app.set_bot_commands([
        BotCommand("start", "Begin verification"),
        BotCommand("help", "Show commands"),
        BotCommand("status", "Check access time"),
        BotCommand("getlink", "[Admin] Create file link"),
        BotCommand("broadcast", "[Admin] Message all users"),
        BotCommand("clone", "Get clone instructions")
    ])

# ================= CORE FUNCTIONS =================
async def safe_send(target, **kwargs):
    """Handle Telegram limits with retry logic"""
    try:
        return await target(**kwargs)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        return await target(**kwargs)
    except (UserNotParticipant, PeerIdInvalid, ChannelPrivate, ChatWriteForbidden):
        return False

async def verify_user(user_id: int):
    """24-hour verification flow with shortener"""
    if Config.SHORTENER_API:
        token = secrets.token_urlsafe(6)
        user_db[user_id] = datetime.now().timestamp() + 86400
        
        bot_username = (await app.get_me()).username
        verify_url = f"https://{Config.SHORTENER_DOMAIN}/api?api={Config.SHORTENER_API}&url=https://t.me/{bot_username}?start=verify_{token}"
        
        await safe_send(
            app.send_message,
            chat_id=user_id,
            text="🔒 Verify your access (valid 24h):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Click to Verify", url=verify_url)
            ]])
        )

# ================= COMMAND HANDLERS =================
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id
    
    # Force join check
    if Config.FORCE_JOIN != "0":
        try:
            await app.get_chat_member(int(Config.FORCE_JOIN), user_id)
        except UserNotParticipant:
            return await message.reply(
                "❌ Please join our channel first",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "Join Channel",
                        url=f"t.me/{(await app.get_chat(Config.FORCE_JOIN)).username}"
                    )
                ]])
            )
    
    # Handle verification tokens
    if len(message.command) > 1:
        if message.command[1].startswith("verify_"):
            user_db[user_id] = datetime.now().timestamp() + 86400
            return await message.reply("✅ Verified for 24 hours!")
        elif message.command[1].startswith("file_"):
            file_id = message.command[1].split("_")[1]
            if file_id in file_db:
                await safe_send(
                    app.copy_message,
                    chat_id=message.chat.id,
                    from_chat_id=Config.DB_CHANNEL_ID,
                    message_id=file_db[file_id]
                )
            return
    
    # New user flow
    if user_id not in user_db:
        await message.reply(
            "🤖 *Cheetah File Storage Bot*\n"
            "\"Lightning fast file sharing with 24h access\"\n\n"
            "🔰 **Developer**: @wleaksOwner\n"
            "💻 **GitHub**: [Aryanwadhonkar/Cheetah](https://github.com/Aryanwadhonkar/Cheetah)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "⭐ Clone on GitHub", 
                    url="https://github.com/Aryanwadhonkar/Cheetah"
                )],
                [InlineKeyboardButton(
                    "🔒 Verify Access", 
                    callback_data="verify"
                )]
            ]),
            disable_web_page_preview=True
        )
    else:
        expiry = datetime.fromtimestamp(user_db[user_id])
        await message.reply(f"✅ Active until: {expiry.strftime('%Y-%m-%d %H:%M')}")

@app.on_callback_query(filters.regex("^verify$"))
async def verify_callback(client, callback: CallbackQuery):
    await verify_user(callback.from_user.id)
    await callback.answer("Verification link sent!")

# [Keep your existing getlink, batch, and broadcast handlers]

# ================= MAIN EXECUTION =================
if __name__ == "__main__":
    # ASCII Art with Credits
    print(r"""
   ____ _    _ _____ _____ _   _ _______ _____  
  / __ \ |  | |  __ \_   _| \ | |__   __|  __ \ 
 / /  \| |  | | |__) || | |  \| |  | |  | |__) |
| |   | |  | |  ___/ | | | . ` |  | |  |  _  / 
 \ \__/| |__| | |    _| |_| |\  |  | |  | | \ \ 
  \____/\____/|_|   |_____|_| \_|  |_|  |_|  \_\
  
  🔹 Developer: @wleaksOwner (Telegram)
  🌐 GitHub: Aryanwadhonkar/Cheetah
  📌 Repository: https://github.com/Aryanwadhonkar/Cheetah
    """)
    
    # Final credit validation
    validate_credits()
    
    # Start the bot
    app.start()
    app.run(set_bot_commands())
