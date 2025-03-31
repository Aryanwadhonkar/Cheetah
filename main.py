#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
import hashlib
import inspect
from pyrogram import Client, idle, filters
from config import Config

print("🛠️ DEBUG MODE ACTIVATED")
print("✅ OS imported")
from dotenv import load_dotenv
print("✅ dotenv imported")
load_dotenv()
print("✅ .env loaded")
print(f"CREDIT_HASH={os.getenv('CREDIT_HASH')}")
print(f"BOT_TOKEN exists? {'BOT_TOKEN' in os.environ}")

# ==================== CREDIT PROTECTION ====================
def validate_credits():
    required = {
        'developer': '@wleaksOwner',
        'github': 'Aryanwadhonkar/Cheetah',
        'repo': 'https://github.com/Aryanwadhonkar/Cheetah'
    }
    current_hash = hashlib.sha256(str(required).encode()).hexdigest()
    
    # Multi-layer verification
    if not hasattr(Config, 'CREDIT_HASH') or Config.CREDIT_HASH != current_hash:
        raise RuntimeError("Credit verification failed!")
    
    # Source code check
    with open(inspect.getsourcefile(inspect.currentframe()), 'r') as f:
        if '@wleaksOwner' not in f.read():
            raise RuntimeError("Source modification detected!")

try:
    validate_credits()
except Exception as e:
    print(f"CREDIT PROTECTION: {str(e)}")
    sys.exit(1)


# ==================== BOT INITIALIZATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Client(
    "cheetah_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)


# ==================== DISPLAY CREDITS ====================
def display_credits():
    credit_art = r"""
   _____ _    _ ______ _____  _   _   _____ ______ 
  / ____| |  | |  ____|  __ \| \ | | / ____|  ____|
 | |    | |__| | |__  | |__) |  \| | |  __| |__   
 | |    |  __  |  __| |  ___/| . ` | | |_ |  __|  
 | |____| |  | | |____| |    | |\  | |__| | |____ 
  \_____|_|  |_|______|_|    |_| \_|\_____|______|
  
  >> DEVELOPED BY @wleaksOwner <<
  >> GITHUB: Aryanwadhonkar/Cheetah <<
  >> HASH: d77629bd9696cd8efcb27fdcd20d4f8e21132213e80cebeb5e89a02ec218416e <<
    """
    print(credit_art)

display_credits()


# ==================== ERROR HANDLER ====================
async def error_handler(func, message, e):
    logger.error(f"Error in {func.__name__}: {str(e)}")
    await message.reply("⚠️ An error occurred. Please try again later.")


# ==================== START COMMAND ====================
@app.on_message(filters.command("start"))
async def start(client, message):
    try:
        if message.from_user.id in Config.ADMINS:
            await message.reply("👑 Admin mode activated!")
        else:
            await message.reply(f"👋 Welcome!\n\n{Config.CREDIT}\n\nUse /token to get access.")
    except Exception as e:
        await error_handler(start, message, e)


# ==================== MAIN LOOP ====================
async def run_bot():
    await app.start()
    
    # Set bot commands
    await app.set_bot_commands([
        ("start", "Start the bot"),
        ("token", "Get access token"),
        ("language", "Change language")
    ])
    
    logger.info("Cheetah Bot Started!")
    await idle()
    await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
