import os
import sys
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import Database
from config import Config
from shortener import shorten_url

# Credit enforcement
CREDIT = "🔹 Developer: @wleaksOwner\n🌐 GitHub: Aryanwadhonkar/Cheetah"
if CREDIT not in __doc__:
    raise RuntimeError("❌ Credit removed! Bot crashed.")

# Initialize
app = Client("CheetahBot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
db = Database(app)

# ====================== HELPER FUNCTIONS ======================
async def is_admin(user_id: int) -> bool:
    return str(user_id) in Config.ADMINS.split(",")

async def enforce_force_sub(user_id: int) -> bool:
    """Check if user joined force-sub channel."""
    if Config.FORCE_SUB == "0":
        return True
    try:
        member = await app.get_chat_member(Config.FORCE_SUB, user_id)
        return member.status not in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]
    except Exception:
        return False

# ====================== COMMAND HANDLERS ======================
@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    user_id = message.from_user.id
    if not await enforce_force_sub(user_id):
        await message.reply(
            "❗ Join our channel first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"t.me/{Config.FORCE_SUB}")]
            ])
        )
        return

    if await is_admin(user_id):
        await message.reply("👑 **Admin Panel**")
    else:
        token = os.urandom(8).hex()
        await db.add_token(user_id, token)
        short_url = shorten_url(f"https://t.me/{client.me.username}?start=verify_{token}")
        
        await message.reply(
            "🔑 Get your 24-hour access token:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Get Token", url=short_url)]
            ])
        )

@app.on_message(filters.command("getlink") & filters.private & filters.user(Config.ADMINS.split(",")))
async def save_file(client: Client, message: Message):
    """Admins: Store a file and generate link."""
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("❗ Reply to a file.")
        return

    # Save to DB_CHANNEL
    msg = await message.reply_to_message.copy(Config.DB_CHANNEL)
    await db.log_file_link(msg.id, msg.message_id)
    
    # Generate link
    link = f"https://t.me/{client.me.username}?start=file_{msg.id}"
    await message.reply(f"🔗 Permanent Link:\n\n{link}")

@app.on_message(filters.command("broadcast") & filters.private & filters.user(Config.ADMINS.split(",")))
async def broadcast(client: Client, message: Message):
    """Admins: Broadcast to all users."""
    if not message.reply_to_message:
        await message.reply("❗ Reply to a message to broadcast.")
        return

    users = await db.get_all_users()  # Implement this in database.py
    for user_id in users:
        try:
            await message.reply_to_message.copy(user_id)
        except Exception:
            pass  # Skip failed sends

@app.on_message(filters.command("ban") & filters.private & filters.user(Config.ADMINS.split(",")))
async def ban_user(client: Client, message: Message):
    """Admins: Ban a user."""
    if len(message.command) < 2:
        await message.reply("❗ Usage: /ban <user_id>")
        return

    user_id = int(message.command[1])
    await db.ban_user(user_id)
    await message.reply(f"✅ Banned user {user_id}.")

# ====================== TOKEN & FILE ACCESS ======================
@app.on_message(filters.private & filters.regex(r'^/start verify_'))
async def verify_token(client: Client, message: Message):
    """Verify user token from shortener."""
    token = message.text.split("_")[1]
    user_id = message.from_user.id
    
    if await db.validate_token(user_id, token):
        await message.reply("✅ Access granted for 24 hours!")
    else:
        await message.reply("❌ Invalid token.")

@app.on_message(filters.private & filters.regex(r'^/start file_'))
async def send_file(client: Client, message: Message):
    """Send file if user has access."""
    user_id = message.from_user.id
    file_id = int(message.text.split("_")[1])
    
    # Check access
    if not (await db.is_premium(user_id) or await db.validate_token(user_id)):
        await message.reply("❌ Get a token first!")
        return

    # Fetch file
    message_id = await db.get_file_message_id(file_id)
    if not message_id:
        await message.reply("❌ File not found!")
        return

    # Send file (with auto-delete if enabled)
    sent_msg = await client.copy_message(
        chat_id=user_id,
        from_chat_id=Config.DB_CHANNEL,
        message_id=message_id
    )

    if Config.AUTO_DELETE != "0":
        await asyncio.sleep(int(Config.AUTO_DELETE) * 60)
        await sent_msg.delete()

# ====================== START BOT ======================
if __name__ == "__main__":
    print("""
   ____ _    _ ______ _____ _______ _____ _    _ 
  / ____| |  | |  ____|  __ \__   __|_   _| |  | |
 | |    | |__| | |__  | |__) | | |    | | | |__| |
 | |    |  __  |  __| |  _  /  | |    | | |  __  |
 | |____| |  | | |____| | \ \  | |   _| |_| |  | |
  \_____|_|  |_|______|_|  \_\ |_|  |_____|_|  |_|
    """)
    app.run()
