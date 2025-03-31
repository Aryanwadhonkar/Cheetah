import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram credentials
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Channels
    DB_CHANNEL = int(os.getenv("DB_CHANNEL"))
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))
    
    # Force sub
    FORCE_SUB = os.getenv("FORCE_SUB", "0")
    if FORCE_SUB.isdigit():
        FORCE_SUB = int(FORCE_SUB) if FORCE_SUB != "0" else None
    
    # URL Shortener
    URL_SHORTENER_API = os.getenv("URL_SHORTENER_API")
    URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN")
    
    # Auto delete
    AUTO_DELETE = int(os.getenv("AUTO_DELETE", "0")) if os.getenv("AUTO_DELETE") else None
    
    # Admins
    ADMINS = [int(admin) for admin in os.getenv("ADMINS").split(",")] if os.getenv("ADMINS") else []
    
    # Premium members
    PREMIUM_MEMBERS = [int(member) for member in os.getenv("PREMIUM_MEMBERS", "").split(",") if member]
    
    # Credit protection
    CREDIT = "@wleaksOwner | github.com/Aryanwadhonkar/Cheetah"
