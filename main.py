import os
import sys
import uuid
import time
import logging
import asyncio
import requests
from functools import wraps
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)
from telegram.error import TelegramError
from commands import get_command_list  # Importing the command list function

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_CHANNEL = int(os.getenv("DB_CHANNEL"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))
FORCE_SUB = os.getenv("FORCE_SUB", "0")
if FORCE_SUB != "0":
    try:
        FORCE_SUB = int(FORCE_SUB)
    except Exception:
        FORCE_SUB = FORCE_SUB.strip()
AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", "0"))  # in minutes
URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN")
URL_SHORTENER_API = os.getenv("URL_SHORTENER_API")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMINS", "").split(",") if x.strip()]

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global dictionaries for token management, banned users, and premium members.
tokens = {}  # token -> { 'data': file_id or [file_ids], 'timestamp': unix_time, 'type': 'single'|'batch' }
banned_users = set()
premium_members = set()


def check_credit():
    """
    Integrity check that verifies the source code includes the proper credit.
    If the word "CHEETAH" is missing, the bot will terminate.
    """
    try:
        with open(__file__, "r", encoding="utf-8") as f:
            code = f.read()
        if "CHEETAH" not in code:
            logger.error("Credit for CHEETAH has been tampered with. Crashing bot.")
            sys.exit("Credit removed")
    except Exception as e:
        logger.error("Credit check failed: " + str(e))
        sys.exit("Credit check failed")


def print_ascii_art():
    """
    Prints the ASCII art with proper 'CHEETAH' spelling and developer credit.
    """
    art = r"""
   ____ _   _ ______ _______ _   _ _     
  / ___| | | |  ____|__   __| \ | | |    
 | |   | |_| | |__     | |  |  \| | |    
 | |   |  _  |  __|    | |  | . ` | |    
 | |___| | | | |       | |  | |\  | |____
  \____|_| |_|_|       |_|  |_| \_|______|
    """
    print(art)
    print("Developer: @wleaksOwner | GitHub: Aryanwadhonkar/Cheetah")


def shorten_url(long_url: str) -> str:
    """
    Shortens a given URL using the provided URL shortener API details.
    If it fails, returns the original URL.
    """
    try:
        payload = {"url": long_url, "domain": URL_SHORTENER_DOMAIN}
        headers = {"Authorization": f"Bearer {URL_SHORTENER_API}"}
        response = requests.post(f"https://{URL_SHORTENER_DOMAIN}/api", json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("short_url", long_url)
        else:
            return long_url
    except Exception as e:
        logger.error("URL shortening failed: " + str(e))
        return long_url


async def force_sub_check(update: Update, context: CallbackContext) -> bool:
    """
    If FORCE_SUB is set, check that the user is a member of the specified channel.
    """
    if FORCE_SUB != "0":
        try:
            member = await context.bot.get_chat_member(FORCE_SUB, update.effective_user.id)
            if member.status == "left":
                keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_SUB}")]]
                await update.message.reply_text(
                    "Please join our channel to use this bot.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                return False
        except TelegramError:
            await update.message.reply_text("Error verifying your subscription. Try again later.")
            return False
    return True


async def start(update: Update, context: CallbackContext) -> None:
    """
    The /start command handler.
    
    • If the command has a token argument, the bot verifies its validity (24-hour duration).
      Sends media using file_id from DB channel and schedules auto deletion.
      Sent media has protected content enabled (preventing forwarding/saving).
    
    • If no argument is provided, a welcome message is shown.
    """
    if FORCE_SUB != "0":
        valid = await force_sub_check(update, context)
        if not valid:
            return

    if update.effective_user.id in banned_users:
        await update.message.reply_text("You are banned from using this bot.")
        return

    # Maintain a record of users for broadcast or stats
    context.bot_data.setdefault("users", set()).add(update.effective_user.id)

    args = context.args
    if args:
        token = args[0]
        token_data = tokens.get(token)
        if token_data and (time.time() - token_data["timestamp"] <= 86400):
            data = token_data["data"]
            try:
                if isinstance(data, list):
                    # Batch files – send each file with protected content enabled.
                    for msg_id in data:
                        await context.bot.copy_message(
                            chat_id=update.effective_chat.id,
                            from_chat_id=DB_CHANNEL,
                            message_id=msg_id,
                            protect_content=True,
                        )
                else:
                    sent_msg = await context.bot.copy_message(
                        chat_id=update.effective_chat.id,
                        from_chat_id=DB_CHANNEL,
                        message_id=data,
                        protect_content=True,
                    )
                # Schedule auto deletion if enabled
                if AUTO_DELETE_TIME > 0:
                    context.job_queue.run_once(
                        lambda ctx: asyncio.create_task(
                            ctx.bot.delete_message(chat_id=update.effective_chat.id, message_id=sent_msg.message_id)
                        ),
                        AUTO_DELETE_TIME * 60,
                    )
                await context.bot.send_message(LOG_CHANNEL, f"User {update.effective_user.id} accessed token {token}")
                del tokens[token]  # Delete token after successful usage
            except TelegramError as e:
                logger.error(f"Error sending file: {e}")
                await update.message.reply_text("Error sending the file. Possibly due to Telegram restrictions.")
        else:
            await update.message.reply_text("Invalid or expired token.")
    else:
        await update.message.reply_text("Welcome to CHEETAH Bot! Use /help to see available commands.")


def admin_only(func):
    """
    Decorator to restrict command access to admins.
    """
    @wraps(func)
    async def wrapped(update: Update, context: CallbackContext):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("You are not authorized to use this command.")
            return
        return await func(update, context)

    return wrapped


async def help_command(update: Update, context: CallbackContext) -> None:
    """
    /help command for all users.

    Sends a list of available commands with descriptions and authorization levels.
    """
    command_list = get_command_list()
    await update.message.reply_text(f"Available Commands:\n{command_list}")


def error_handler(update: object, context: CallbackContext) -> None:
    """
    Basic error handler to log exceptions.
    """
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


def main() -> None:
    # Check that credit is intact before starting.
    check_credit()
    
print_ascii_art()

application = Application.builder().token(BOT_TOKEN).build()

# Command handlers

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("getlink", getlink))
application.add_handler(CommandHandler("firstbatch", firstbatch))
application.add_handler(CommandHandler("lastbatch", lastbatch))
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(CommandHandler("stats", stats))
application.add_handler(CommandHandler("ban", ban))
application.add_handler(CommandHandler("premiummembers", premiummembers))
application.add_handler(CommandHandler("restart", restart))
application.add_handler(CommandHandler("language", language))

# Add help command handler here
application.add_handler(CommandHandler("help", help_command))  # Adding help command handler

# Handler to capture batch files (only activated when in batch mode)
application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, batch_file_handler))

application.add_error_handler(error_handler)

application.run_polling()

if __name__ == '__main__':
   main()
    
