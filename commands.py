# commands.py

# Define a list of commands with their descriptions and authorization levels
COMMANDS = {
    "/start": {
        "description": "Start interacting with the bot.",
        "authorized": "All users"
    },
    "/getlink": {
        "description": "Store a media file and generate a token link (admin only).",
        "authorized": "Admins"
    },
    "/firstbatch": {
        "description": "Start batch mode to store multiple files (admin only).",
        "authorized": "Admins"
    },
    "/lastbatch": {
        "description": "End batch mode and generate a token link for all stored files (admin only).",
        "authorized": "Admins"
    },
    "/broadcast": {
        "description": "Send a message to all users (admin only).",
        "authorized": "Admins"
    },
    "/stats": {
        "description": "Show bot statistics (admin only).",
        "authorized": "Admins"
    },
    "/ban": {
        "description": "Ban a user by their ID (admin only).",
        "authorized": "Admins"
    },
    "/premiummembers": {
        "description": "Manage premium members (admin only).",
        "authorized": "Admins"
    },
    "/restart": {
        "description": "Restart the bot (admin only).",
        "authorized": "Admins"
    },
    "/language": {
        "description": "Set your preferred language.",
        "authorized": "All users"
    }
}

def get_command_list():
    """
    Generates a formatted string of available commands.
    
    Returns:
        str: A string representation of commands with descriptions and authorization levels.
    """
    command_list = ""
    for command, info in COMMANDS.items():
        command_list += f"{command} - {info['description']} (Authorized: {info['authorized']})\n"
    
    return command_list.strip()
