import os
import asyncio
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import Database
from shortener import shorten_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cheetah.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Credit enforcement
CREDIT = "🔹 Developer: @wleaksOwner\n🌐 GitHub: Aryanwadhonkar/Cheetah"
if CREDIT not in __doc__:
    logger.critical("CREDIT REMOVED - BOT CRASHED")
    raise RuntimeError("❌ Credit removed! Bot crashed.")

class CheetahBot(Client):
    def __init__(self):
        super().__init__(
            name="CheetahBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            sleep_threshold=60,
            workers=4,
            plugins=dict(root="plugins")
        )
        self.db = Database(self)
        logger.info("Bot initialized")

app = CheetahBot()

# ====================== COMMAND HANDLERS ======================
@app.on_message(filters.command("start"))
async def start(client: CheetahBot, message: Message):
    try:
        user_id = message.from_user.id
        logger.info(f"Start command from {user_id}")
        
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
            await client.db.add_token(user_id, token)
            short_url = shorten_url(f"https://t.me/{client.me.username}?start=verify_{token}")
            
            await message.reply(
                "🔑 Get your 24-hour access token:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Get Token", url=short_url)]
                ])
            )
    except Exception as e:
        logger.error(f"Start error: {e}")
        await message.reply("❌ An error occurred. Please try again.")

# [Add all other handlers with similar try/except blocks]

# ====================== HELPER FUNCTIONS ======================
async def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMINS

async def enforce_force_sub(user_id: int) -> bool:
    """Check if user joined force-sub channel."""
    if Config.FORCE_SUB == "0":
        return True
    try:
        member = await app.get_chat_member(Config.FORCE_SUB, user_id)
        return member.status not in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]
    except Exception as e:
        logger.error(f"Force sub check failed: {e}")
        return False

if __name__ == "__main__":
    print(r"""
   ____ _    _ ______ _____ _______ _____ _    _ 
  / ____| |  | |  ____|  __ \__   __|_   _| |  | |
 | |    | |__| | |__  | |__) | | |    | | | |__| |
 | |    |  __  |  __| |  _  /  | |    | | |  __  |
 | |____| |  | | |____| | \ \  | |   _| |_| |  | |
  \_____|_|  |_|______|_|  \_\ |_|  |_____|_|  |_|
    """)
    
    try:
        logger.info("Starting Cheetah Bot")
        app.run()
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
        raise
