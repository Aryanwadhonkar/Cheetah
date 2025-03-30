import sqlite3
from pyrogram import Client
from config import Config

class Database:
    def __init__(self, bot: Client):
        self.bot = bot
        self.conn = sqlite3.connect("cheetah.db")
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Initialize SQLite tables."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                is_banned BOOLEAN DEFAULT FALSE,
                is_premium BOOLEAN DEFAULT FALSE
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                expires_at DATETIME
            )
        """)
        self.conn.commit()

    async def log_file_link(self, file_id: int, message_id: int):
        """Permanently store file_id → message_id in LOG_CHANNEL."""
        await self.bot.send_message(
            Config.LOG_CHANNEL,
            f"📁 FILE {file_id} {message_id}",
            disable_notification=True
        )

    async def get_file_message_id(self, file_id: int) -> int:
        """Fetch message_id from LOG_CHANNEL for a file_id."""
        async for msg in self.bot.search_messages(
            Config.LOG_CHANNEL,
            query=f"📁 FILE {file_id}"
        ):
            return int(msg.text.split()[-1])
        return None

    # ... (Add other methods: add_user, add_token, etc.)
