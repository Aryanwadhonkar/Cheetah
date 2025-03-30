# 🐆 Cheetah File Storage Bot 

**Lightning-fast Telegram file storage with time-limited access**  
*A secure solution for sharing files with expiration and access control*

![Demo](https://img.shields.io/badge/Status-Active-brightgreen) 
![icense](https://img.shields.io/badge/License-MIT-blue)
![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0-red)

<div align="center">
  <img src="https://github.com/Aryanwadhonkar/Cheetah/assets/your-repo/cheetah-banner.gif" width="400">
</div>

⚙️Key Features Added
Feature	Implementation
Auto-delete	Files auto-delete after AUTO_DELETE minutes (configurable in .env).
URL Shortener	Token links are shortened using shorten_url() (set API in .env).
Force-subscribe	Users must join FORCE_SUB channel before using the bot.
24-hour Tokens	Non-premium users get tokens that expire after 24 hours.
Premium Members	Admins can whitelist users with /premium.
Admin Commands	/broadcast, /ban, /stats, /restart, etc.
Credit Enforcement	Bot crashes if credit is removed (check CREDIT variable).

🗣️🔥 Core Features

✅ Hybrid Storage
SQLite: Users, tokens, bans (fast queries).
Telegram LOG_CHANNEL: Permanent file links (no data loss).

✅ Access Control
24-hour tokens for regular users.
Premium users bypass tokens (admins can assign via /premium).

✅ Admin Commands
Command	Usage
/getlink	Save a file
/ban	Ban a user
/broadcast	Message all users

✅ Security
Files are never stored locally (only in Telegram cloud).
Force-subscribe to channels (optional).


🛠 Deployment

💀Termux (Android)
pkg install python git
git clone https://github.com/YourRepo/Cheetah.git
cd Cheetah
pip install -r requirements.txt
python bot.py

☠️Linux/Windows
pip install -r requirements.txt
python bot.py


🔄 How Data Flows
Admin uploads cat.jpg → stored in DB_CHANNEL (Message ID 123).
Bot logs 📁 FILE 789 123 to LOG_CHANNEL.
User requests /start file_789 → bot checks SQLite for access → sends file from DB_CHANNEL.


📌 Need Help?
Error handling: The bot automatically catches FloodWait, UserBlocked, etc.
Scaling: SQLite works for 100K+ users (optimized queries).
Backups: Use Telegram’s "Export Chat" for LOG_CHANNEL backups.
Let me know if you want to add more features! 🚀
