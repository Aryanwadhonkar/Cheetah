#!/usr/bin/env python3
import os
import sys
import time
import logging
import asyncio
import hashlib
import inspect
from pyrogram import Client, idle
from config import Config

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

# Display credits
def show_credits():
    credit_art = r"""
   _____ _    _ ______ _____  _   _   _____ ______ 
  / ____| |  | |  ____|  __ \| \ | | / ____|  ____|
 | |    | |__| | |__  | |__) |  \| | |  __| |__   
 | |    |  __  |  __| |  ___/| . ` | | |_ |  __|  
 | |____| |  | | |____| |    | |\  | |__| | |____ 
  \_____|_|  |_|______|_|    |_| \_|\_____|______|
  
  >> DEVELOPED BY @wleaksOwner <<
  >> GITHUB: Aryanwadhonkar/Cheetah <<
    """
    print(credit_art)

show_credits()

app = Client(
    "cheetah_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# ==================== ERROR HANDLER ====================
async def error_handler(func, message, e):
    logger.error(f"Error in {func.__name__}: {str(e)}")
    await message.reply("⚠️ An error occurred. Please try again later.")

# ==================== START COMMAND ====================
@app.on_message(filters.command("start"))
async def start(client, message):
    try:
        if await auth.is_admin(message.from_user.id):
            await message.reply("👋 Admin mode activated!")
        else:
            await message.reply("👋 Welcome! Use /token to get access.")
    except Exception as e:
        await error_handler(start, message, e)

# ==================== MAIN LOOP ====================
async def startup():
    await app.start()
    from commands import set_bot_commands
    await set_bot_commands(app)
    logger.info("Cheetah Bot Started!")

async def shutdown():
    await app.stop()
    logger.info("Cheetah Bot Stopped!")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(startup())
        idle()
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown())
    finally:
        loop.close()
