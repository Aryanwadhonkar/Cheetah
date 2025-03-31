import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

class CreditSystem:
    @staticmethod
    def verify():
        # Critical - Do not modify these values
        CREDIT_DATA = {
            'developer': '@wleaksOwner',
            'github': 'Aryanwadhonkar/Cheetah',
            'repository': 'https://github.com/Aryanwadhonkar/Cheetah'
        }
        
        # Generate current hash
        current_hash = hashlib.sha256(str(CREDIT_DATA).encode()).hexdigest()
        
        # Verify against stored hash
        if not hasattr(Config, 'CREDIT_HASH') or Config.CREDIT_HASH != current_hash:
            print(f"NICE TRY DIDDY!")
            print(f"Expected: {current_hash}")
            print(f"Got: {getattr(Config, 'CREDIT_HASH', 'None')}")
            raise RuntimeError("Credit verification failed - Bot stopped")

class Config(CreditSystem):
    # Telegram API
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Channels
    DB_CHANNEL = int(os.getenv("DB_CHANNEL", 0))
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", 0))
    
    # Credits (DO NOT MODIFY)
    CREDIT = "@wleaksOwner | github.com/Aryanwadhonkar/Cheetah"
    CREDIT_HASH = os.getenv("CREDIT_HASH", "")
    
    # Other settings
    FORCE_SUB = os.getenv("FORCE_SUB", "0")
    URL_SHORTENER_API = os.getenv("URL_SHORTENER_API", "")
    URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN", "")
    AUTO_DELETE = int(os.getenv("AUTO_DELETE", 0))
    ADMINS = [int(admin) for admin in os.getenv("ADMINS", "").split(",") if admin]
    PREMIUM_MEMBERS = [int(member) for member in os.getenv("PREMIUM_MEMBERS", "").split(",") if member]

# Verify credits on import
Config.verify()
