from pyrogram import filters
from pyrogram.types import Message
from config import Config

class AdminTools:
    def __init__(self):
        self._credit_check()

    def _credit_check(self):
        if not hasattr(Config, 'CREDIT_HASH'):
            self._crash()

    def _crash(self):
        import sys
        sys.exit("Credit protection triggered!")

    async def broadcast(self, client, message):
        self._credit_check()
        # Implementation here

    async def stats(self, client, message):
        self._credit_check()
        # Implementation here

def register_handlers(client):
    admin = AdminTools()
    
    @client.on_message(filters.command("broadcast") & filters.private)
    async def broadcast_wrapper(client, message):
        await admin.broadcast(client, message)
    
    @client.on_message(filters.command("stats") & filters.private)
    async def stats_wrapper(client, message):
        await admin.stats(client, message)
