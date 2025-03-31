GNU nano 8.3                                                 database.py
import asyncio
import sqlite3
from datetime import datetime, timedelta
from pyrogram import Client
import logging
logging.basicConfig(level=logging.INFO)

class Database:
    def __init__(self, bot: Client):
        self.bot = bot
        self.conn = sqlite3.connect(
            "cheetah.db",
            check_same_thread=False,
            timeout=30,  # Wait 30 seconds if locked
            isolation_level=None  # Disable transactions for better concurrency
        )
        self.conn.execute("PRAGMA journal_mode=WAL")  # Better write performance
        self.conn.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
        self.cursor = self.conn.cursor()
        self._create_tables()
        logging.info("Database connection established")

    def _create_tables(self):
        """Initialize database tables with error handling"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    is_banned BOOLEAN DEFAULT FALSE,
                    is_premium BOOLEAN DEFAULT FALSE,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) STRICT;
            """)
            # Add other tables with STRICT mode for better type checking
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                ) STRICT;
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            raise

    async def log_file_link(self, file_id: int, message_id: int):
        """Store file mapping in LOG_CHANNEL with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self.bot.send_message(
                    Config.LOG_CHANNEL,
                    f"📁 FILE {file_id} {message_id}",
                    disable_notification=True
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"Failed to log file after {max_retries} attempts: {e}")
                    raise
                await asyncio.sleep(1)

    def __del__(self):
        """Cleanup database connection"""
        try:
            self.conn.close()
            logging.info("Database connection closed")
        except:
            pass

    # [Add your other methods with similar error handling]
