import os
import sys
import uuid
import time
import logging
import asyncio
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

    keyboard = [[InlineKeyboardButton("Get 24-Hour Token", url="https://example.com")]]  # Replace with actual URL shortener link
    await update.message.reply_text(
        "Welcome! Click the button below to get your 24-hour token.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


@admin_only
async def getlink(update: Update, context: CallbackContext) -> None:
    """
    /getlink command (admin only).

    Generates a unique token link for accessing media files.
    """
    
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a media message with /getlink")
        return

    msg = update.message.reply_to_message

    file_id = None 
    if msg.document: 
        file_id = msg.document.file_id 
    elif msg.photo: 
        file_id = msg.photo[-1].file_id 
    elif msg.video: 
        file_id = msg.video.file_id 
    else: 
        await update.message.reply_text("No valid media found in replied message.") 
        return 

    try: 
        forwarded = await context.bot.forward_message( 
            chat_id=DB_CHANNEL, 
            from_chat_id=msg.chat.id, 
            message_id=msg.message_id 
        ) 

        token = str(uuid.uuid4())[:8] 
        tokens[token] = {"data": forwarded.message_id, "timestamp": time.time(), "type": "single"} 

        special_link = f"https://t.me/{context.bot.username}?start={token}" 
        await update.message.reply_text(f"File stored!\nToken Link: {special_link}", disable_web_page_preview=True) 

        await context.bot.send_message( 
            chat_id=LOG_CHANNEL, 
            text=f"Admin {update.effective_user.id} stored a file. Token: {token}" 
        ) 

    except Exception as e: 
        logger.error(f"Error in /getlink: {e}") 
        await update.message.reply_text("Failed to store file due to an error.")


@admin_only
async def broadcast(update: Update, context: CallbackContext) -> None:
     """
     /broadcast command (admin only).

     Sends a message to all users registered with the bot.
     Includes an optional button.
     """
     if not context.args:
         await update.message.reply_text("Provide a message to broadcast.")
         return
    
     message = " ".join(context.args)
     users = context.bot_data.get("users", set())
     sent_count = 0
    
     for user_id in users:
         try:
             keyboard_option = [[InlineKeyboardButton(text="Click Here", url="https://example.com")]]  # Example button; replace with actual link
             await context.bot.send_message(user_id, message, reply_markup=InlineKeyboardMarkup(keyboard_option))
             sent_count += 1
         except Exception as e:
             logger.error(f"Error sending broadcast to {user_id}: {e}")
             
     await update.message.reply_text(f"Broadcast sent to {sent_count} users.")


@admin_only 
async def stats(update: Update, context: CallbackContext) -> None: 
      """ 
      /stats command (admin only): 
        
      Displays bot statistics such as total users and active tokens. 
      """ 
        
      total_users = len(context.bot_data.get("users", set())) 
      active_tokens = len(tokens) 
        
      stats_text = f"Total Users: {total_users}\nActive Tokens: {active_tokens}" 
        
      await update.message.reply_text(stats_text)


@admin_only  
async def restart(update: Update, context: CallbackContext) -> None:

      """  
      /restart command (admin only):  
        
      Restarts the bot.  
      """  
        
      await update.message.reply_text("Restarting bot...")  
        
      os.execv(sys.executable, [sys.executable] + sys.argv)


def error_handler(update: object, context: CallbackContext) -> None:
   """
   Basic error handler to log exceptions.
   """
   logger.error(msg="Exception while handling an update:", exc_info=context.error)


def main() -> None:
   application = Application.builder().token(BOT_TOKEN).build()

   # Command handlers
   application.add_handler(CommandHandler("start", start))
   application.add_handler(CommandHandler("getlink", getlink))
   application.add_handler(CommandHandler("broadcast", broadcast))
   application.add_handler(CommandHandler("stats", stats))
   application.add_handler(CommandHandler("restart", restart))

   application.add_error_handler(error_handler)

   application.run_polling()


if __name__ == "__main__":
   main()
    
