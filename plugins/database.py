import logging
from config import Config

class ChannelDB:
    def __init__(self):
        self._setup_credit_protection()
        self.logger = logging.getLogger(__name__)

    def _setup_credit_protection(self):
        # Hidden credit marker
        self.__credit_marker = "ARYAN_WADHONKAR_CHEETAH_DB"
        
    def _verify_credits(self):
        if not hasattr(self, '__credit_marker'):
            self.logger.error("Database credit marker missing!")
            self._corrupt_db()

    def _corrupt_db(self):
        # Make DB operations fail if credits are removed
        raise RuntimeError("Database protection triggered")

    async def store_file(self, client, message, user_id):
        self._verify_credits()
        
        try:
            # Forward to DB channel
            forwarded = await message.forward(Config.DB_CHANNEL)
            
            # Log metadata
            log_msg = f"📁 New file stored\n" \
                     f"├ User: {user_id}\n" \
                     f"├ File ID: {forwarded.message_id}\n" \
                     f"└ Credit: {Config.CREDIT}"
                     
            await client.send_message(Config.LOG_CHANNEL, log_msg)
            return forwarded.message_id
            
        except Exception as e:
            self.logger.error(f"Store file error: {str(e)}")
            raise

    async def get_file(self, client, file_id):
        self._verify_credits()
        
        try:
            return await client.get_messages(Config.DB_CHANNEL, int(file_id))
        except Exception as e:
            self.logger.error(f"Get file error: {str(e)}")
            return None

database = ChannelDB()

# Shortcut functions
async def store_file(*args, **kwargs):
    return await database.store_file(*args, **kwargs)

async def get_file(*args, **kwargs):
    return await database.get_file(*args, **kwargs)
