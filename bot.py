import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytz
from dotenv import load_dotenv
from telegram import (
    Update,
    Chat,
    ChatPermissions,
    Message,
    InputMediaDocument,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ChatAction, ChatMemberStatus, ChatType
from telegram.error import (
    TelegramError,
    BadRequest,
    Forbidden,
    NetworkError,
    RetryAfter,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
TOKEN = os.getenv("BOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS").split(",")))
CHANNEL_ID = os.getenv("CHANNEL_ID")
FORCE_SUB = os.getenv("FORCE_SUB", "0")
AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", 0))  # in minutes
URL_SHORTENER_API = os.getenv("URL_SHORTENER_API")
URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Database setup (using SQLite for simplicity)
import sqlite3

conn = sqlite3.connect("file_store.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS files (
        file_id TEXT PRIMARY KEY,
        file_name TEXT,
        file_type TEXT,
        file_size INTEGER,
        message_id INTEGER,
        date_added TIMESTAMP,
        added_by INTEGER
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        last_interaction TIMESTAMP,
        is_premium INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS tokens (
        user_id INTEGER,
        token TEXT,
        expiry TIMESTAMP,
        PRIMARY KEY (user_id, token)
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS file_links (
        file_id TEXT,
        short_url TEXT,
        PRIMARY KEY (file_id, short_url)
    )
"""
)

conn.commit()

# ASCII Art
CHEETAH_ART = """
   ____ _    _ _____ _____ _______ _    _ 
  / ____| |  | |_   _|  __ \__   __| |  | |
 | |    | |__| | | | | |  | | | |  | |__| |
 | |    |  __  | | | | |  | | | |  |  __  |
 | |____| |  | |_| |_| |__| | | |  | |  | |
  \_____|_|  |_|_____|_____/  |_|  |_|  |_|
"""

print(CHEETAH_ART)

# Helper functions
async def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

async def is_premium(user_id: int) -> bool:
    cursor.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1 if result else False

async def is_banned(user_id: int) -> bool:
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1 if result else False

async def update_user_info(user_id: int, username: str, first_name: str, last_name: str):
    cursor.execute(
        """
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_interaction)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (user_id, username, first_name, last_name),
    )
    conn.commit()

async def generate_token(user_id: int) -> str:
    import secrets
    token = secrets.token_urlsafe(16)
    expiry = datetime.now(pytz.utc) + timedelta(hours=24)
    
    cursor.execute(
        "INSERT INTO tokens (user_id, token, expiry) VALUES (?, ?, ?)",
        (user_id, token, expiry),
    )
    conn.commit()
    return token

async def validate_token(user_id: int, token: str) -> bool:
    cursor.execute(
        "SELECT expiry FROM tokens WHERE user_id = ? AND token = ?",
        (user_id, token),
    )
    result = cursor.fetchone()
    if not result:
        return False
    
    expiry = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
    return datetime.now(pytz.utc) < expiry

async def shorten_url(long_url: str) -> str:
    if not URL_SHORTENER_API or not URL_SHORTENER_DOMAIN:
        return long_url
    
    try:
        import requests
        response = requests.post(
            URL_SHORTENER_API,
            json={"long_url": long_url},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 200:
            return response.json().get("short_url", long_url)
    except Exception as e:
        logger.error(f"URL shortening failed: {e}")
    return long_url

async def check_force_sub(user_id: int) -> bool:
    if FORCE_SUB == "0":
        return True
    
    try:
        chat_member = await context.bot.get_chat_member(FORCE_SUB, user_id)
        return chat_member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]
    except Exception as e:
        logger.error(f"Force sub check failed: {e}")
        return False

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update_user_info(user.id, user.username, user.first_name, user.last_name)
    
    if await is_banned(user.id):
        await update.message.reply_text("You are banned from using this bot.")
        return
    
    if not await check_force_sub(user.id):
        await update.message.reply_text(
            "Please join our channel first to use this bot.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_SUB}")]
            ])
        )
        return
    
    if await is_admin(user.id) or await is_premium(user.id):
        await update.message.reply_text(
            "Welcome back! You can use /getlink to store files or send me a file directly."
        )
    else:
        token = await generate_token(user.id)
        await update.message.reply_text(
            f"Welcome! Your access token is valid for 24 hours:\n\n"
            f"`{token}`\n\n"
            "Use this token to access files. After 24 hours, you'll need a new token.",
            parse_mode="Markdown"
        )

async def getlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can use this command.")
        return
    
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("Please reply to a file with this command.")
        return
    
    try:
        file = update.message.reply_to_message.document
        file_id = file.file_id
        
        # Store file in channel
        message = await context.bot.send_document(
            chat_id=CHANNEL_ID,
            document=file_id,
            caption=f"File: {file.file_name}\nSize: {file.file_size} bytes",
            disable_notification=True
        )
        
        # Save to database
        cursor.execute(
            "INSERT INTO files (file_id, file_name, file_type, file_size, message_id, date_added, added_by) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'), ?)",
            (file_id, file.file_name, file.mime_type, file.file_size, message.message_id, user.id),
        )
        conn.commit()
        
        # Generate access link
        bot_username = context.bot.username
        deep_link = f"https://t.me/{bot_username}?start={file_id}"
        short_url = await shorten_url(deep_link)
        
        cursor.execute(
            "INSERT INTO file_links (file_id, short_url) VALUES (?, ?)",
            (file_id, short_url),
        )
        conn.commit()
        
        await update.message.reply_text(
            f"File stored successfully!\n\n"
            f"Access link: {short_url}\n"
            f"File ID: `{file_id}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in getlink: {e}")
        await update.message.reply_text("Failed to store file. Please try again.")

async def firstbatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can use this command.")
        return
    
    context.user_data["batch_files"] = []
    await update.message.reply_text(
        "Batch mode started. Send me files one by one. When done, use /lastbatch to finish."
    )

async def lastbatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can use this command.")
        return
    
    if "batch_files" not in context.user_data or not context.user_data["batch_files"]:
        await update.message.reply_text("No files in batch. Use /firstbatch first.")
        return
    
    try:
        # Prepare media group
        media_group = []
        for file_id, file_name, mime_type in context.user_data["batch_files"]:
            media_group.append(InputMediaDocument(media=file_id, caption=file_name))
        
        # Send to channel
        messages = await context.bot.send_media_group(
            chat_id=CHANNEL_ID,
            media=media_group,
            disable_notification=True
        )
        
        # Save to database and generate links
        links = []
        for i, (file_id, file_name, mime_type) in enumerate(context.user_data["batch_files"]):
            cursor.execute(
                "INSERT INTO files (file_id, file_name, file_type, file_size, message_id, date_added, added_by) "
                "VALUES (?, ?, ?, ?, ?, datetime('now'), ?)",
                (file_id, file_name, mime_type, 0, messages[i].message_id, user.id),
            )
            
            bot_username = context.bot.username
            deep_link = f"https://t.me/{bot_username}?start={file_id}"
            short_url = await shorten_url(deep_link)
            
            cursor.execute(
                "INSERT INTO file_links (file_id, short_url) VALUES (?, ?)",
                (file_id, short_url),
            )
            links.append(short_url)
        
        conn.commit()
        
        await update.message.reply_text(
            "Batch files stored successfully!\n\n" +
            "\n".join(links)
        )
        
        # Clean up
        del context.user_data["batch_files"]
    except Exception as e:
        logger.error(f"Error in lastbatch: {e}")
        await update.message.reply_text("Failed to store batch files. Please try again.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can use this command.")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message to broadcast.")
        return
    
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    
    success = 0
    failed = 0
    for (user_id,) in users:
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=update.message.reply_to_message.chat_id,
                message_id=update.message.reply_to_message.message_id
            )
            success += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
            failed += 1
    
    await update.message.reply_text(
        f"Broadcast completed!\n\nSuccess: {success}\nFailed: {failed}"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can use this command.")
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
    premium_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
    banned_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM files")
    total_files = cursor.fetchone()[0]
    
    await update.message.reply_text(
        f"📊 Bot Statistics:\n\n"
        f"👥 Total Users: {total_users}\n"
        f"⭐ Premium Users: {premium_users}\n"
        f"🚫 Banned Users: {banned_users}\n"
        f"📁 Total Files: {total_files}"
    )

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    
    try:
        user_id = int(context.args[0])
        cursor.execute(
            "UPDATE users SET is_banned = 1 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        await update.message.reply_text(f"User {user_id} has been banned.")
    except Exception as e:
        logger.error(f"Error in ban: {e}")
        await update.message.reply_text("Failed to ban user. Please check the user ID.")

async def premiummembers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can use this command.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /premiummembers <user_id> <add/remove>")
        return
    
    try:
        user_id = int(context.args[0])
        action = context.args[1].lower()
        
        if action == "add":
            cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, is_premium) VALUES (?, 1)",
                (user_id,)
            )
            await update.message.reply_text(f"User {user_id} added to premium members.")
        elif action == "remove":
            cursor.execute(
                "UPDATE users SET is_premium = 0 WHERE user_id = ?",
                (user_id,)
            )
            await update.message.reply_text(f"User {user_id} removed from premium members.")
        else:
            await update.message.reply_text("Invalid action. Use 'add' or 'remove'.")
        
        conn.commit()
    except Exception as e:
        logger.error(f"Error in premiummembers: {e}")
        await update.message.reply_text("Failed to update premium status. Please check the user ID.")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can use this command.")
        return
    
    await update.message.reply_text("Restarting bot...")
    os.execv(sys.executable, ['python'] + sys.argv)

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Available languages:\n\n"
        "1. English (default)\n"
        "2. Spanish\n"
        "3. French\n\n"
        "Select a language by sending its number."
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("Only admins can store files.")
        return
    
    if "batch_files" in context.user_data:
        # In batch mode
        if update.message.document:
            context.user_data["batch_files"].append((
                update.message.document.file_id,
                update.message.document.file_name,
                update.message.document.mime_type
            ))
            await update.message.reply_text("File added to batch. Send more or use /lastbatch.")
    else:
        # Single file mode
        if update.message.document:
            await getlink(update, context)

async def handle_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update_user_info(user.id, user.username, user.first_name, user.last_name)
    
    if await is_banned(user.id):
        await update.message.reply_text("You are banned from using this bot.")
        return
    
    if not await check_force_sub(user.id):
        await update.message.reply_text(
            "Please join our channel first to access files.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_SUB}")]
            ])
        )
        return
    
    file_id = context.args[0] if context.args else None
    if not file_id:
        await start(update, context)
        return
    
    # Check if user has valid token or is premium/admin
    if not (await is_admin(user.id) or await is_premium(user.id)):
        cursor.execute(
            "SELECT token FROM tokens WHERE user_id = ? AND expiry > datetime('now')",
            (user.id,)
        )
        valid_token = cursor.fetchone()
        
        if not valid_token:
            token = await generate_token(user.id)
            await update.message.reply_text(
                f"You need a valid token to access files. Here's your new token (valid for 24 hours):\n\n"
                f"`{token}`\n\n"
                "Click the link again after receiving this token.",
                parse_mode="Markdown"
            )
            return
    
    # Send the file
    try:
        cursor.execute(
            "SELECT file_id, file_name FROM files WHERE file_id = ?",
            (file_id,)
        )
        file_data = cursor.fetchone()
        
        if not file_data:
            await update.message.reply_text("File not found.")
            return
        
        file_id, file_name = file_data
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        
        sent_message = await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_id,
            caption=file_name,
            protect_content=True  # Prevent forwarding
        )
        
        # Auto-delete if enabled
        if AUTO_DELETE_TIME > 0:
            await asyncio.sleep(AUTO_DELETE_TIME * 60)
            try:
                await sent_message.delete()
            except Exception as e:
                logger.error(f"Failed to auto-delete message: {e}")
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await update.message.reply_text("Failed to send file. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    
    if isinstance(error, BadRequest) and "Message to delete not found" in str(error):
        return
    
    logger.error(msg="Exception while handling an update:", exc_info=error)
    
    if isinstance(error, Forbidden):
        # User blocked the bot or doesn't have permission
        if update.effective_message:
            user_id = update.effective_message.from_user.id
            cursor.execute(
                "UPDATE users SET is_banned = 1 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
        return
    
    if isinstance(error, RetryAfter):
        await asyncio.sleep(error.retry_after + 1)
        return
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "An error occurred. Please try again later."
            )
        except Exception as e:
            logger.error(f"Error while sending error message: {e}")

def main():
    # Create application
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", handle_deep_link))
    application.add_handler(CommandHandler("getlink", getlink))
    application.add_handler(CommandHandler("firstbatch", firstbatch))
    application.add_handler(CommandHandler("lastbatch", lastbatch))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("premiummembers", premiummembers))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CommandHandler("language", language))
    
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    application.add_error_handler(error_handler)
    
    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
