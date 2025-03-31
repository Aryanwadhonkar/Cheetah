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
from telegram.ext import Application, CommandHandler, CallbackContext

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_CHANNEL = int(os.getenv("DB_CHANNEL"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))
FORCE_SUB = os.getenv("FORCE_SUB", "0")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMINS", "").split(",") if x.strip()]
AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", "0"))  # in minutes
URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN")
URL_SHORTENER_API = os.getenv("URL_SHORTENER_API")

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global dictionaries for token management, banned users, and premium members.
tokens = {}
banned_users = set()
premium_members = set()

# Uptime tracking
start_time = time.time()


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
        except Exception as e:
            logger.error(f"Force sub check failed: {e}")
            await update.message.reply_text("Error verifying subscription.")
            return False
    return True


def shorten_url(long_url: str) -> str:
    """
    Shortens a given URL using the provided URL shortener API details.
    If it fails, returns the original URL.
    """
    try:
        payload = {"url": long_url}
        headers = {"Authorization": f"Bearer {URL_SHORTENER_API}"}
        response = requests.post(f"https://{URL_SHORTENER_DOMAIN}/api", json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("short_url", long_url)
        else:
            logger.error(f"Failed to shorten URL. Status code: {response.status_code}")
            return long_url
    except Exception as e:
        logger.error(f"Error shortening URL: {e}")
        return long_url


async def start(update: Update, context: CallbackContext) -> None:
    """
    The /start command handler.

    Sends a welcome message and provides a button to get a 24-hour token.
    """
    
    if FORCE_SUB != "0":
        valid = await force_sub_check(update, context)
        if not valid:
            return

    if update.effective_user.id in banned_users:
        await update.message.reply_text("You are banned from using this bot.")
        return

    # Maintain a record of users for stats
    context.bot_data.setdefault("users", set()).add(update.effective_user.id)

    # Generate a shortened URL for token generation (example purpose)
    long_url = f"https://example.com/get-token?user_id={update.effective_user.id}"
    short_url = shorten_url(long_url)

    keyboard = [[InlineKeyboardButton("Get 24-Hour Token", url=short_url)]]
    await update.message.reply_text(
        "Welcome! Click the button below to get your 24-hour token.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


@admin_only
async def broadcast(update: Update, context: CallbackContext) -> None:
     """
     /broadcast command (admin only).

     Sends a message to all users registered with the bot.
     Includes an optional button with shortened URLs.
     """
     if not context.args:
         await update.message.reply_text("Provide a message to broadcast.")
         return
    
     message = " ".join(context.args)
     users = context.bot_data.get("users", set())
     sent_count = 0
    
     for user_id in users:
         try:
             # Example of broadcasting with shortened link in button
             long_url = f"https://example.com/promo?user_id={user_id}"
             short_url = shorten_url(long_url)

             keyboard_option = [[InlineKeyboardButton(text="Click Here", url=short_url)]]
             await context.bot.send_message(user_id, message, reply_markup=InlineKeyboardMarkup(keyboard_option))
             sent_count += 1
         except Exception as e:
             logger.error(f"Error sending broadcast to {user_id}: {e}")
             
     await update.message.reply_text(f"Broadcast sent to {sent_count} users.")


def error_handler(update: object, context: CallbackContext) -> None:
   """
   Basic error handler to log exceptions.
   """
   logger.error(msg="Exception while handling an update:", exc_info=context.error)


def main() -> None:
   application = Application.builder().token(BOT_TOKEN).build()

   # Command handlers
   application.add_handler(CommandHandler("start", start))
   application.add_handler(CommandHandler("broadcast", broadcast))

   application.add_error_handler(error_handler)

   application.run_polling()


if __name__ == "__main__":
   main()
