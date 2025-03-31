import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

class CreditSystem:
    @staticmethod
    def verify_credits():
        required_credits = {
            'developer': '@wleaksOwner',
            'github': 'Aryanwadhonkar/Cheetah',
            'repository': 'https://github.com/Aryanwadhonkar/Cheetah'
        }
        
        current_hash = hashlib.sha256(str(required_credits).encode()).hexdigest()
        if not hasattr(Config, 'CREDIT_HASH') or Config.CREDIT_HASH != current_hash:
            raise RuntimeError("Credit verification failed! Bot will not start.")

class Config(CreditSystem):
    # Telegram credentials
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Credit protection
    CREDIT_HASH = '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'  # SHA-256 of credits
    
    # ... rest of the config ...
