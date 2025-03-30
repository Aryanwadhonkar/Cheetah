import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    FloodWait, 
    UserIsBlocked, 
    PeerIdInvalid, 
    ChatWriteForbidden,
    ChannelPrivate
)

import shortener
from database import Database
from config import Config

# ASCII Art
CHEETAH_ART = """
   ____ _    _ ______ _____ _______ _____ _    _ 
  / ____| |  | |  ____|  __ \__   __|_   _| |  | |
 | |    | |__| | |__  | |__) | | |    | | | |__| |
 | |    |  __  |  __| |  _  /  | |    | | |  __  |
 | |____| |  | | |____| | \ \  | |   _| |_| |  | |
  \_____|_|  |_|______|_|  \_\ |_|  |_____|_|  |_|
"""

print(CHEETAH_ART)

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Pyrogram client
app = Client(
    "CheetahBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Initialize database
db = Database()

# Helper functions
async def is_admin(user_id: int) -> bool:
    return str(user_id) in Config.ADMINS.split(',')

async def save_file_to_channel(file: Union[Message, str]) -> int:
    try:
        if isinstance(file, Message):
            msg = await file.copy(Config.DB_CHANNEL)
        else:
            msg = await app.send_message(Config.DB_CHANNEL, file)
        return msg.id
    except Exception as e:
        logger.error(f"Error saving file to channel: {e}")
        raise

async def generate_token(user_id: int) -> str:
    token = os.urandom(16).hex()
    expiry = datetime.now() + timedelta(hours=24)
    await db.add_token(user_id, token, expiry)
    return token

async def verify_token(user_id: int, token: str) -> bool:
    return await db.validate_token(user_id, token)

async def get_file_message(file_id: int) -> Message:
    return await app.get_messages(Config.DB_CHANNEL, file_id)

async def send_log(message: str):
    try:
        await app.send_message(Config.DB_CHANNEL, message)
    except Exception as e:
        logger.error(f"Error sending log: {e}")

# Command handlers
@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_admin(user_id):
        text = "👑 **Admin Panel**\n\nCommands:\n/getlink - Store single file\n/firstbatch - Start batch upload\n/lastbatch - End batch upload\n/broadcast - Broadcast message\n/stats - Get bot stats\n/ban - Ban user\n/premiummembers - Manage premium\n/restart - Restart bot"
    else:
        if Config.FORCE_SUB and Config.FORCE_SUB != "0":
            try:
                member = await client.get_chat_member(Config.FORCE_SUB, user_id)
                if member.status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]:
                    await message.reply("❗ Please join our channel first to use this bot.", 
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{Config.FORCE_SUB}")]
                        ]))
                    return
            except Exception as e:
                logger.error(f"Force sub check error: {e}")
        
        text = "🔐 **File Access Bot**\n\nTo access files, you need a valid token. Tokens expire after 24 hours.\n\nClick below to get your access token:"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Get Access Token", url=f"https://{Config.URL_SHORTENER_DOMAIN}/token")]
        ])
    
    await message.reply(text, reply_markup=reply_markup if not await is_admin(user_id) else None)

@app.on_message(filters.command("getlink") & filters.private)
async def get_link(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Only admins can use this command.")
        return
    
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("❗ Reply to a media file with this command.")
        return
    
    try:
        file_id = await save_file_to_channel(message.reply_to_message)
        file_link = f"https://t.me/{client.me.username}?start=file_{file_id}"
        await message.reply(f"🔗 File Link:\n\n{file_link}")
        await send_log(f"📁 New file stored by admin {message.from_user.id}\nFile ID: {file_id}")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command(["firstbatch", "lastbatch"]) & filters.private)
async def batch_upload(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Only admins can use this command.")
        return
    
    user_id = message.from_user.id
    command = message.command[0]
    
    if command == "firstbatch":
        await db.start_batch(user_id)
        await message.reply("📦 Batch upload started. Send all files now and use /lastbatch when done.")
    else:
        batch_files = await db.get_batch(user_id)
        if not batch_files:
            await message.reply("❗ No batch upload in progress.")
            return
        
        file_ids = []
        for file_msg in batch_files:
            try:
                file_id = await save_file_to_channel(file_msg)
                file_ids.append(file_id)
            except Exception as e:
                logger.error(f"Error saving batch file: {e}")
                continue
        
        batch_link = f"https://t.me/{client.me.username}?start=batch_{'_'.join(map(str, file_ids))}"
        await message.reply(f"📦 Batch Files Link:\n\n{batch_link}")
        await send_log(f"📦 New batch stored by admin {user_id}\nFile IDs: {file_ids}")
        await db.clear_batch(user_id)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Only admins can use this command.")
        return
    
    if not message.reply_to_message:
        await message.reply("❗ Reply to a message with this command to broadcast it.")
        return
    
    users = await db.get_all_users()
    total = len(users)
    success = 0
    
    await message.reply(f"📢 Starting broadcast to {total} users...")
    
    for user_id in users:
        try:
            await message.reply_to_message.copy(user_id)
            success += 1
            await asyncio.sleep(0.5)  # Avoid flood
        except (UserIsBlocked, PeerIdInvalid, ChannelPrivate):
            await db.delete_user(user_id)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"Broadcast error to {user_id}: {e}")
    
    await message.reply(f"✅ Broadcast completed.\nSuccess: {success}\nFailed: {total - success}")

@app.on_message(filters.command("stats") & filters.private)
async def stats(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Only admins can use this command.")
        return
    
    total_users = await db.total_users_count()
    total_files = await db.total_files_count()
    active_tokens = await db.active_tokens_count()
    premium_users = await db.premium_users_count()
    
    stats_text = f"""
📊 **Bot Statistics**

👥 Total Users: {total_users}
⭐ Premium Users: {premium_users}
🗃️ Total Files: {total_files}
🔑 Active Tokens: {active_tokens}
"""
    await message.reply(stats_text)

@app.on_message(filters.command("ban") & filters.private)
async def ban_user(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Only admins can use this command.")
        return
    
    if len(message.command) < 2:
        await message.reply("❗ Usage: /ban <user_id>")
        return
    
    try:
        user_id = int(message.command[1])
        await db.ban_user(user_id)
        await message.reply(f"✅ User {user_id} banned successfully.")
        await send_log(f"🔨 User {user_id} banned by admin {message.from_user.id}")
    except ValueError:
        await message.reply("❗ Invalid user ID.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("premiummembers") & filters.private)
async def premium_members(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Only admins can use this command.")
        return
    
    if len(message.command) < 3:
        await message.reply("❗ Usage: /premiummembers <add/remove/list> <user_id>")
        return
    
    action = message.command[1].lower()
    
    if action == "list":
        premium_users = await db.get_premium_users()
        if not premium_users:
            await message.reply("No premium users found.")
            return
        
        users_text = "\n".join([f"• {user_id}" for user_id in premium_users])
        await message.reply(f"⭐ Premium Users:\n\n{users_text}")
        return
    
    try:
        user_id = int(message.command[2])
        if action == "add":
            await db.add_premium_user(user_id)
            await message.reply(f"✅ User {user_id} added to premium.")
            await send_log(f"⭐ User {user_id} added to premium by admin {message.from_user.id}")
        elif action == "remove":
            await db.remove_premium_user(user_id)
            await message.reply(f"✅ User {user_id} removed from premium.")
            await send_log(f"⭐ User {user_id} removed from premium by admin {message.from_user.id}")
        else:
            await message.reply("❗ Invalid action. Use add/remove/list.")
    except ValueError:
        await message.reply("❗ Invalid user ID.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("restart") & filters.private)
async def restart_bot(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Only admins can use this command.")
        return
    
    await message.reply("🔄 Restarting bot...")
    await send_log(f"🔃 Bot restarted by admin {message.from_user.id}")
    os.execv(sys.executable, [sys.executable, '-m', 'bot'])

@app.on_message(filters.command("language") & filters.private)
async def change_language(client: Client, message: Message):
    # Placeholder for language functionality
    await message.reply("🌐 Language settings will be available in future updates.")

# Handle file access
@app.on_message(filters.private & filters.regex(r'^/start (file|batch)_'))
async def handle_file_access(client: Client, message: Message):
    user_id = message.from_user.id
    parts = message.text.split('_')
    access_type = parts[0].split(' ')[1]
    ids = parts[1]
    
    # Check premium status
    is_premium = await db.is_premium_user(user_id)
    
    if not is_premium:
        # Check token for non-premium users
        if not await db.has_valid_token(user_id):
            await message.reply("🔒 Your access token has expired. Please get a new one.", 
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Get New Token", url=f"https://{Config.URL_SHORTENER_DOMAIN}/token")]
                ]))
            return
    
    try:
        if access_type == "file":
            file_id = int(ids)
            file_msg = await get_file_message(file_id)
            sent_msg = await file_msg.copy(user_id)
            
            if Config.AUTO_DELETE and Config.AUTO_DELETE != "0":
                await asyncio.sleep(int(Config.AUTO_DELETE) * 60)
                try:
                    await sent_msg.delete()
                except Exception as e:
                    logger.error(f"Error deleting auto-delete message: {e}")
            
        elif access_type == "batch":
            file_ids = list(map(int, ids.split('_')))
            for file_id in file_ids:
                try:
                    file_msg = await get_file_message(file_id)
                    sent_msg = await file_msg.copy(user_id)
                    
                    if Config.AUTO_DELETE and Config.AUTO_DELETE != "0":
                        await asyncio.sleep(int(Config.AUTO_DELETE) * 60)
                        try:
                            await sent_msg.delete()
                        except Exception as e:
                            logger.error(f"Error deleting auto-delete batch message: {e}")
                    
                    await asyncio.sleep(1)  # Avoid flood
                except Exception as e:
                    logger.error(f"Error sending batch file {file_id}: {e}")
                    continue
        
        await send_log(f"📤 File(s) accessed by user {user_id} (Premium: {is_premium})")
    except Exception as e:
        await message.reply(f"❌ Error accessing file: {e}")
        logger.error(f"File access error: {e}")

# Handle token verification from shortener
@app.on_message(filters.private & filters.regex(r'^/verify '))
async def verify_user_token(client: Client, message: Message):
    token = message.text.split(' ')[1]
    user_id = message.from_user.id
    
    if await verify_token(user_id, token):
        await message.reply("✅ Token verified! You can now access files for 24 hours.")
        await send_log(f"🔑 Token verified for user {user_id}")
    else:
        await message.reply("❌ Invalid or expired token. Please get a new one.")

# Error handlers
@app.on_errors()
async def error_handler(client: Client, error: Exception, update: types.Update):
    logger.error(f"Error: {error}", exc_info=True)
    
    if isinstance(error, FloodWait):
        await asyncio.sleep(error.value)
    elif isinstance(error, (UserIsBlocked, PeerIdInvalid, ChannelPrivate)):
        await db.delete_user(update.from_user.id)
    elif isinstance(error, ChatWriteForbidden):
        logger.error("Bot doesn't have permission to write in chat")

# Start the bot
if __name__ == "__main__":
    logger.info("Starting Cheetah File Store Bot...")
    app.run()
