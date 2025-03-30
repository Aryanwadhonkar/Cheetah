import sqlite3
from datetime import datetime, timedelta
from pyrogram import Client
from config import Config

class Database:
    def __init__(self, bot: Client):
        self.bot = bot
        self.conn = sqlite3.connect("cheetah.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Initialize all SQLite tables."""
        # Users table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                is_banned BOOLEAN DEFAULT FALSE,
                is_premium BOOLEAN DEFAULT FALSE,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tokens table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                expires_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        # File access logs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                file_id INTEGER,
                accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        self.conn.commit()

    async def log_file_link(self, file_id: int, message_id: int):
        """Store file_id → message_id permanently in LOG_CHANNEL."""
        await self.bot.send_message(
            Config.LOG_CHANNEL,
            f"📁 FILE {file_id} {message_id}",
            disable_notification=True
        )

    async def get_file_message_id(self, file_id: int) -> int:
        """Fetch message_id from LOG_CHANNEL for a file."""
        async for msg in self.bot.search_messages(
            Config.LOG_CHANNEL,
            query=f"📁 FILE {file_id}"
        ):
            return int(msg.text.split()[-1])
        return None

    async def add_token(self, user_id: int, token: str, expires_in: int = 24):
        """Add a 24-hour access token for a user."""
        expires_at = datetime.now() + timedelta(hours=expires_in)
        self.cursor.execute(
            "INSERT INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at)
        )
        self.conn.commit()

    async def validate_token(self, user_id: int, token: str) -> bool:
        """Check if a token is valid."""
        self.cursor.execute(
            "SELECT 1 FROM tokens WHERE user_id=? AND token=? AND expires_at > datetime('now')",
            (user_id, token)
        )
        return bool(self.cursor.fetchone())

    async def add_premium_user(self, user_id: int):
        """Grant premium access (bypass tokens)."""
        self.cursor.execute(
            "INSERT OR REPLACE INTO users (user_id, is_premium) VALUES (?, TRUE)",
            (user_id,)
        )
        self.conn.commit()

    # ... (Add other methods: ban_user, broadcast, stats, etc.)
