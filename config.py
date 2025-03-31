import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    ADMINS = os.getenv("ADMINS").split(",")
    DB_CHANNEL = int(os.getenv("DB_CHANNEL"))
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))
    FORCE_SUB = os.getenv("FORCE_SUB")
    AUTO_DELETE = int(os.getenv("AUTO_DELETE", 0))
