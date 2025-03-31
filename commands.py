from pyrogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from config import Config

class CommandSystem:
    def __init__(self):
        self._verify_credits()

    def _verify_credits(self):
        if not hasattr(Config, 'CREDIT') or '@wleaksOwner' not in Config.CREDIT:
            import os
            os.kill(os.getpid(), 9)

    async def set_commands(self, client):
        try:
            # Admin commands
            admin_cmds = [
                BotCommand("getlink", "Generate file link"),
                BotCommand("batch", "Batch file upload"),
                BotCommand("broadcast", "Broadcast message"),
                BotCommand("stats", "View statistics"),
                BotCommand("ban", "Ban a user"),
                BotCommand("restart", "Restart bot"),
                BotCommand("premium", "Manage premium")
            ]
            
            # User commands
            user_cmds = [
                BotCommand("start", "Start the bot"),
                BotCommand("token", "Get access token"),
                BotCommand("language", "Change language")
            ]
            
            # Set commands
            await client.set_bot_commands(
                commands=user_cmds,
                scope=BotCommandScopeDefault()
            )
            
            for admin in Config.ADMINS:
                await client.set_bot_commands(
                    commands=admin_cmds + user_cmds,
                    scope=BotCommandScopeChat(chat_id=admin)
                )
                
        except Exception as e:
            print(f"Command Error: {str(e)}")
            raise

async def set_bot_commands(client):
    cmd = CommandSystem()
    await cmd.set_commands(client)
