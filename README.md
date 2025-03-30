# 🐆 Cheetah File Storage Bot 

**Lightning-fast Telegram file storage with time-limited access**  
*A secure solution for sharing files with expiration and access control*

![Demo](https://img.shields.io/badge/Status-Active-brightgreen) 
![icense](https://img.shields.io/badge/License-MIT-blue)
![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0-red)

<div align="center">
  <img src="https://github.com/Aryanwadhonkar/Cheetah/assets/your-repo/cheetah-banner.gif" width="400">
</div>

## 🔥 Key Features
- **Military-Grade Security**  
  - Files stored in private channels
  - Auto-expiring access links (24h default)
  - Credit enforcement system

- **Smart Access Control**  
  - Force join channels (optional)
  - URL shortener integration
  - Admin-only file uploads

- **High Performance**  
  - Batch uploads (10 files at once)
  - Flood wait protection
  - Efficient memory usage

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
