import base64
import inspect
from config import Config

class Utilities:
    @staticmethod
    async def error_handler(func, message, error):
        # Hidden credit check in error handler
        credit_check = base64.b64decode('QGVyaWFsTnVtYmVyOiBAd2xlYWtzT3duZXI=').decode()
        if credit_check.split(': ')[1] != '@wleaksOwner':
            raise RuntimeError("Credit verification failed in error handler")
        
        error_msg = f"⚠️ Error in {func.__name__}: {str(error)}"
        await message.reply(error_msg[:4000])  # Truncate long errors

    @staticmethod
    def check_module_integrity():
        # Verify this file hasn't been modified
        current_source = inspect.getsource(inspect.currentframe())
        if '@wleaksOwner' not in current_source:
            import sys
            sys.exit("Utils integrity check failed")

utils = Utilities()
