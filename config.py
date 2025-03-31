import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

class CreditSystem:
    @staticmethod
    def verify():
        required = {
            'developer': '@wleaksOwner',
            'github': 'Aryanwadhonkar/Cheetah'
        }
        current_hash = hashlib.sha256(str(required).encode()).hexdigest()
        if not hasattr(Config, 'CREDIT_HASH') or Config.CREDIT_HASH != current_hash:
            raise RuntimeError("Credit verification failed!")

class Config(CreditSystem):
    # Telegram
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Channels
    DB_CHANNEL = int(os.getenv("DB_CHANNEL", 0))
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", 0))
    
    # Credits
    CREDIT_HASH = 'd3a8bd2e0f1b39aa2322d9274e5a5e0a6e5b5e5e'  # SHA-1 of credits
    CREDIT = "@wleaksOwner | github.com/Aryanwadhonkar/Cheetah"
    
    # Force Sub
    FORCE_SUB = os.getenv("FORCE_SUB", "0")
    
    # Shortener
    URL_SHORTENER_API = os.getenv("URL_SHORTENER_API", "")
    URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN", "")
    
    # Auto Delete
    AUTO_DELETE = int(os.getenv("AUTO_DELETE", 0))
    
    # Admins
    ADMINS = [int(admin) for admin in os.getenv("ADMINS", "").split(",") if admin]
    
    # Premium
    PREMIUM_MEMBERS = [int(member) for member in os.getenv("PREMIUM_MEMBERS", "").split(",") if member]

# Verify on import
Config.verify()
