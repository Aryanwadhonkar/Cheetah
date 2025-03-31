import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

class CreditSystem:
    @staticmethod
    def verify():
        # Critical - Use ordered dict for consistent hashing
        CREDIT_DATA = (
            ("developer", "@wleaksOwner"),
            ("github", "Aryanwadhonkar/Cheetah"),
            ("repository", "https://github.com/Aryanwadhonkar/Cheetah")
        )
        
        # Generate stable JSON-style hash
        json_str = "{%s}" % ", ".join(f'"{k}": "{v}"' for k,v in CREDIT_DATA)
        current_hash = hashlib.sha256(json_str.encode()).hexdigest()
        
        # Enhanced error detection
        if not hasattr(Config, 'CREDIT_HASH') or Config.CREDIT_HASH != current_hash:
            print(f"⛔ Modified: {getattr(Config, 'CREDIT_HASH', '')[:12]}... (Expected: {current_hash[:12]}...)")
            print("Nice try Diddy!")
            os._exit(1)  # Immediate exit without traceback

class Config(CreditSystem):
    # Telegram API (Keep these first)
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Credits protection (Must come after API keys)
    CREDIT_HASH = os.getenv("CREDIT_HASH", "")
    
    # Channels
    DB_CHANNEL = int(os.getenv("DB_CHANNEL", 0))
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", 0))
    
    # Other settings
    FORCE_SUB = os.getenv("FORCE_SUB", "0")
    URL_SHORTENER_API = os.getenv("URL_SHORTENER_API", "")
    URL_SHORTENER_DOMAIN = os.getenv("URL_SHORTENER_DOMAIN", "")
    AUTO_DELETE = int(os.getenv("AUTO_DELETE", 0))
    ADMINS = [int(admin) for admin in os.getenv("ADMINS", "").split(",") if admin]
    PREMIUM_MEMBERS = [int(member) for member in os.getenv("PREMIUM_MEMBERS", "").split(",") if member]

# Verify before any config usage
Config.verify()
