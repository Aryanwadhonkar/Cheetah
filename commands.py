from pyrogram.types import BotCommand
from config import Config

async def set_bot_commands(client):
    # Admin commands (only visible to admins in private chats)
    admin_commands = [
        BotCommand("getlink", "Generate link for a single file"),
        BotCommand("firstbatch", "Start batch file upload"),
        BotCommand("lastbatch", "End batch file upload"),
        BotCommand("broadcast", "Broadcast message to all users"),
        BotCommand("stats", "Get bot statistics"),
        BotCommand("ban", "Ban a user from using the bot"),
        BotCommand("restart", "Restart the bot"),
        BotCommand("premiummembers", "Manage premium members")
    ]
    
    # User commands
    user_commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("token", "Get 24-hour access token"),
        BotCommand("language", "Change language settings")
    ]
    
    try:
        # Set commands for all users
        await client.set_bot_commands(
            commands=user_commands,
            scope=BotCommandScopeDefault()
        )
        
        # Set commands specifically for admins
        for admin_id in Config.ADMINS:
            await client.set_bot_commands(
                commands=admin_commands + user_commands,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
    except Exception as e:
        print(f"Failed to set bot commands: {e}")
