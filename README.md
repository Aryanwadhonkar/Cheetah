# 🐆 Cheetah File Storage Bot 

**Lightning-fast Telegram file storage with time-limited access**  
*A secure solution for sharing files with expiration and access control*

![Demo](https://img.shields.io/badge/Status-Active-brightgreen) 
![icense](https://img.shields.io/badge/License-MIT-blue)
![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0-red)

<div align="center">
  <img src="https://github.com/Aryanwadhonkar/Cheetah/assets/your-repo/cheetah-banner.gif" width="400">
</div>
✅ Core Features Implemented
File Storage System

Files stored in your private Telegram channel (CHANNEL_ID=-1002348593955)

Users access files via unique links (e.g., t.me/yourbot?start=FILE_ID)

No files stored in MongoDB (only metadata and links).

Access Control

Admins (you) can upload files via:

/getlink (single file)

/firstbatch + /lastbatch (multiple files in one link)

Regular users require 24-hour tokens (auto-expire via MongoDB TTL index).

Premium members bypass token checks (assign with /premiummembers).

Security & Restrictions

No forwarding of files (protect_content=True).

Force-subscribe (optional via FORCE_SUB=channel_id).

Auto-delete sent files after AUTO_DELETE_TIME minutes (disabled if 0).

Admin Commands

/broadcast - Send messages to all users.

/stats - View bot analytics (users, files, etc.).

/ban - Ban users from accessing the bot.

/restart - Restart the bot remotely.

User Experience

/start - Generates a 24-hour access token.

/language - Change bot language (placeholder for future support).

MongoDB Optimization

Only 4 collections: users, tokens, files, premium.

Automatic cleanup of expired tokens (TTL index).

Minimal data stored (no file contents, only Telegram file IDs).

Credit Enforcement

Bot crashes if credits (@wleaksOwner) are removed (logic embedded in critical functions).

Termux-Compatible

Lightweight, handles Telegram API limits.




## 🛠️ Installation
Install Termux from F-Droid (not Play Store for latest version)

Run these commands in Termux:
pkg update
pkg upgrade
pkg install python git
git clone https://github.com/Aryanwadhonkar/Cheetah
cd Cheetah
pip install -r requirements.txt
cp .env.example .env
# Edit .env file with your details
nano .env
# Save with Ctrl+O, Enter, Ctrl+X
python bot.py


⚙️Features Implemented

File Storage: Files stored in private Telegram channel

Access Control:

Admins can upload files (/getlink, /firstbatch, /lastbatch)

Regular users need 24-hour tokens

Premium members bypass token requirement

Security:

Restricted content (no forwarding)

Token-based access

Force subscription option

Admin Commands:

/broadcast - Send messages to all users

/stats - View bot statistics

/ban - Ban users

/premiummembers - Manage premium users

/restart - Restart the bot

User Commands:

/start - Get started with the bot

/language - Change language

Optimizations:

Error handling for Telegram restrictions

Auto-delete media option

URL shortening support

Batch file uploads
