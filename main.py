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
# Comma-separated list of admin user IDs
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
                await update.message.reply_text("Please join our channel to use this bot.",
                                                reply_markup=InlineKeyboardMarkup(keyboard))
                return False
        except TelegramError:
            await update.message.reply_text("Error verifying your subscription. Try again later.")
            return False
    return True

async def start(update: Update, context: CallbackContext) -> None:
    """
    The /start command handler.
    
    • If the command has a token argument, the bot verifies its validity (24-hour duration).
    • It then sends the media using the file_id from the DB channel and schedules auto deletion.
      The sent media has the protected content flag enabled (preventing forwarding/saving).
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
                            protect_content=True
                        )
                    # Schedule deletion for each message if auto deletion is enabled.
                    if AUTO_DELETE_TIME:
                        context.job_queue.run_once(
                            lambda ctx: asyncio.create_task(
                                ctx.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                            ),
                            AUTO_DELETE_TIME * 60,
                        )
                else:
                    sent_msg = await context.bot.copy_message(
                        chat_id=update.effective_chat.id,
                        from_chat_id=DB_CHANNEL,
                        message_id=data,
                        protect_content=True
                    )
                    if AUTO_DELETE_TIME:
                        context.job_queue.run_once(
                            lambda ctx: asyncio.create_task(
                                ctx.bot.delete_message(chat_id=update.effective_chat.id, message_id=sent_msg.message_id)
                            ),
                            AUTO_DELETE_TIME * 60,
                        )
                await context.bot.send_message(
                    chat_id=LOG_CHANNEL,
                    text=f"User {update.effective_user.id} accessed token {token}"
                )
                # Delete token after successful usage.
                del tokens[token]
            except TelegramError as e:
                logger.error("Error sending file: " + str(e))
                await update.message.reply_text("Error sending the file. Possibly due to Telegram restrictions.")
        else:
            await update.message.reply_text("Invalid or expired token.")
    else:
        await update.message.reply_text("Welcome to CHEETAH Bot! Use the available commands to interact.")

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

@admin_only
async def getlink(update: Update, context: CallbackContext) -> None:
    """
    /getlink command (admin only):
    
    • Must be used as a reply to a media message.
    • Forwards the media to the private DB channel, generates a unique token, and returns a token link.
    • The token link (which can be shortened) is valid for 24 hours.
    """
    
   # Check if there is a reply to a media message 
   if not update.message.reply_to_message: 
       await update.message.reply_text("Reply to a media message with /getlink") 
       return 
    
   msg = update.message.reply_to_message

   # Extract file_id from document, photo or video 
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
       special_link = shorten_url(special_link) 

       await update.message.reply_text(f"File stored!\nToken Link: {special_link}", disable_web_page_preview=True) 

       await context.bot.send_message( 
           chat_id=LOG_CHANNEL, 
           text=f"Admin {update.effective_user.id} stored a file. Token: {token}" 
       ) 

   except TelegramError as e: 
       logger.error("Error in /getlink: " + str(e)) 
       await update.message.reply_text("Failed to store file due to an error.")

@admin_only
async def firstbatch(update: Update, context: CallbackContext) -> None:
     """
     /firstbatch command (admin only):
     
     • Initiates batch mode for storing multiple files.
     """
     context.user_data["batch_files"] = []
     await update.message.reply_text("Batch mode started. Send your files and then use /lastbatch to complete.")

@admin_only
async def lastbatch(update: Update, context: CallbackContext) -> None:
     """
     /lastbatch command (admin only):
     
     • Ends batch mode. Forwards all cached files to the DB channel and generates one token link.
     """
     batch_files = context.user_data.get("batch_files", [])
     if not batch_files:
         await update.message.reply_text("No files received for batch.")
         return
    
     batch_msg_ids = []
     for file_msg in batch_files:
         try:
             forwarded = await context.bot.forward_message(
                 chat_id=DB_CHANNEL,
                 from_chat_id=file_msg.chat.id,
                 message_id=file_msg.message_id
             )
             batch_msg_ids.append(forwarded.message_id)
         except TelegramError as e:
             logger.error("Error forwarding batch file: " + str(e))
             
     token = str(uuid.uuid4())[:8]
     tokens[token] = {"data": batch_msg_ids, "timestamp": time.time(), "type": "batch"}
     special_link = f"https://t.me/{context.bot.username}?start={token}"
     special_link = shorten_url(special_link)
     await update.message.reply_text(f"Batch stored!\nToken Link: {special_link}", disable_web_page_preview=True)
     await context.bot.send_message(
         chat_id=LOG_CHANNEL,
         text=f"Admin {update.effective_user.id} stored a batch. Token: {token}"
     )
     context.user_data["batch_files"] = []  # Reset batch mode

@admin_only
async def batch_file_handler(update: Update, context: CallbackContext) -> None:
     """
     Captures media messages during batch mode.
     Only messages from admins in batch mode will be recorded.
     """
     if "batch_files" in context.user_data:
         context.user_data["batch_files"].append(update.message)
         await update.message.reply_text("File added to batch.")

@admin_only
async def broadcast(update: Update, context: CallbackContext) -> None:
     """
     /broadcast command (admin only):
     
     • Broadcasts a provided message to all users registered with the bot.
     """
     if not context.args:
         await update.message.reply_text("Provide a message to broadcast.")
         return
    
     message = " ".join(context.args)
     users = context.bot_data.get("users", set())
     sent_count = 0
    
     for user_id in users:
         try:
             await context.bot.send_message(user_id, message)
             sent_count += 1
         except TelegramError as e:
             logger.error(f"Error sending broadcast to {user_id}: " + str(e))
             
     await update.message.reply_text(f"Broadcast sent to {sent_count} users.")

@admin_only 
async def stats(update: Update, context: CallbackContext) -> None: 
      """ 
      /stats command (admin only): 
        
      • Shows bot statistics such as total users and active tokens. 
      """ 
        
      total_users = len(context.bot_data.get("users", set())) 
      active_tokens = len(tokens) 
        
      stats_text = f"Total Users: {total_users}\nActive Tokens: {active_tokens}" 
        
      await update.message.reply_text(stats_text)

@admin_only 
async def ban(update: Update, context: CallbackContext) -> None: 
      """ 
      /ban command (admin only): 
        
      • Bans a user by their Telegram ID. 
      Usage: /ban <user_id> 
      """ 
        
      if not context.args: 
          await update.message.reply_text("Provide a user ID to ban.") 
          return 
        
      try: 
          user_id = int(context.args[0]) 
          banned_users.add(user_id) 
          await update.message.reply_text(f"User {user_id} has been banned.") 
        
          await context.bot.send_message( 
              chat_id=LOG_CHANNEL, 
              text=f"User {user_id} banned by admin {update.effective_user.id}" 
          ) 
        
      except ValueError: 
          await update.message.reply_text("Invalid user ID.")

@admin_only  
async def premiummembers(update: Update, context: CallbackContext) -> None:

      """  
      /premiummembers command (admin only):  
        
      • Assigns or removes premium membership.  
      Usage: /premiummembers add <user_id> or /premiummembers remove <user_id>  
      Premium members get files without needing a token.  
      """  

      if len(context.args) < 2:

          await update.message.reply_text("Usage: /premiummembers add|remove <user_id>")  

          return  

      action = context.args[0].lower()  

      try:

          user_id = int(context.args[1])  

          if action == "add":  

              premium_members.add(user_id)

              await update.message.reply_text(f"User {user_id} is now a premium member.")  

          elif action == "remove":

              premium_members.discard(user_id)

              await update.message.reply_text(f"User {user_id} has been removed from premium members.")  

          else:

              await update.message.reply_text("Invalid action. Use add or remove.")  

      except ValueError:

          await update.message.reply_text("Invalid user ID.")

@admin_only  
async def restart(update: Update, context: CallbackContext) -> None:

      """  
      /restart command (admin only):  
        
      • Restarts the bot.  
      """  
        
      await update.message.reply_text("Restarting bot...")  
        
      await context.bot.send_message(LOG_CHANNEL, f"Bot restarted by admin {update.effective_user.id}")  
        
      os.execv(sys.executable, [sys.executable] + sys.argv)

async def language(update: Update, context: CallbackContext) -> None:

      """  
      /language command available to everyone:

      • Allows the user to set their preferred language.  
      """  

      if not context.args:

          await update.message.reply_text("Usage: /language <language_code>")  

          return  

      lang = context.args[0].lower()  

      context.user_data["language"] = lang  

      await update.message.reply_text(f"Language set to {lang}.")

async def help_command(update: Update, context: CallbackContext) -> None:

   """
   /help command for all users:

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
       
