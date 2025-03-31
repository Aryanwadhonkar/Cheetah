import sqlite3
from datetime import datetime, timedelta
from pyrogram import Client

class Database:
    def __init__(self, bot: Client):
        self.bot = bot
        self.conn = sqlite3.connect("cheetah.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Initialize database tables"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                is_banned BOOLEAN DEFAULT FALSE,
                is_premium BOOLEAN DEFAULT FALSE
            )
        """)
        # [Add other tables as per your original code]
        self.conn.commit()

    async def log_file_link(self, file_id: int, message_id: int):
        """Store file mapping in LOG_CHANNEL"""
        await self.bot.send_message(
            Config.LOG_CHANNEL,
            f"📁 FILE {file_id} {message_id}",
            disable_notification=True
        )
    
    # [Add all other methods from your original code]
