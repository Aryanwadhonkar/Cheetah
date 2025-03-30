# 🐆 Cheetah File Storage Bot 

**Lightning-fast Telegram file storage with time-limited access**  
*A secure solution for sharing files with expiration and access control*

![Demo](https://img.shields.io/badge/Status-Active-brightgreen) 
![License](https://img.shields.io/badge/License-MIT-blue)
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

## 🛠️ Installation (Termux)

```bash
# 1. Update packages
pkg update && pkg upgrade -y

# 2. Install dependencies
pkg install python git libjpeg-turbo libcrypt -y

# 3. Install Python requirements
pip install pyrogram tgcrypto python-dotenv

# 4. Clone repository
git clone https://github.com/Aryanwadhonkar/Cheetah.git
cd Cheetah

# 5. Create .env file
cat > .env <<EOF
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
BOT_TOKEN=your_bot_token
DB_CHANNEL_ID=-1001234567890
ADMINS=123456789,987654321
FORCE_JOIN=0  # Set to channel ID if needed
SHORTENER_API=your_api_key  # Optional
SHORTENER_DOMAIN=your.domain  # Optional
EOF

# 6. Start the bot (in background)
tmux new -s cheetah_bot
python main.py
# Press Ctrl+B then D to detach



📝 Configuration Guide
Variable	   Required	     Description
BOT_TOKEN	       ✅	      From @BotFather
API_ID	         ✅	      Get from my.telegram.org
API_HASH	       ✅.     	Get from my.telegram.org
DB_CHANNEL_ID	   ✅.     	Private channel ID (include -100 prefix)
ADMINS	         ✅	      Your Telegram User IDs, comma-separated
FORCE_JOIN	     ❌	      Channel ID to force users to join
SHORTENER_API	   ❌	      Shortener service API key
SHORTENER_DOMAIN ❌	      Your shortener domain

🤖 Bot Commands
For Users
Command	    Description
/start	    Begin verification process
/status	    Check remaining access time
/clone	    Get setup instructions

For Admins
Command	       Description
/getlink	     Generate file access link
/broadcast	   Message all users
/verify [id]	 Manually verify user



🐳 Docker Deployment (Alternative)
docker run -d \
  --name cheetah_bot \
  -v ./data:/app \
  -e BOT_TOKEN=your_token \
  -e API_ID=your_id \
  -e API_HASH=your_hash \
  -e DB_CHANNEL_ID=-1001234567890 \
  aryanwadhonkar/cheetah:latest


🔒 License (Modified MIT)
Original Developer: @wleaksOwner (Telegram)
GitHub: https://github.com/Aryanwadhonkar/Cheetah
- CREDIT LINES MUST REMAIN IN ALL COPIES
- COMMERCIAL USE REQUIRES PERMISSION
- BOTS MUST DISPLAY ORIGINAL DEVELOPER IN /start



🚨 Troubleshooting (Termux)
Issue: Bot crashes on startup
✅ Fix: pkg install libjpeg-turbo then reinstall requirements
Issue: Files not saving
✅ Fix:
Ensure bot is admin in DB channel
Check channel ID includes -100 prefix
Issue: High memory usage
✅ Fix: Run tmux new -s cheetah to isolate session




🌟 Pro Tips
Use termux-wake-lock to prevent Android sleep
Add && python3 -m pip install --upgrade pip before requirements
For better performance:
pkg install clang
export CC=clang
pip install --no-cache-dir -r requirements.txt



📬 Support
For assistance:
👉 Telegram: @wleaksOwner
👉 GitHub: https://github.com/Aryanwadhonkar/Cheetah/issues






### 🔄 Termux Redeployment Guide
If you need to redeploy from scratch:

1. **Clean existing installation**:
   ```bash
   tmux kill-session -t cheetah_bot
   pkill -f main.py
   rm -rf ~/Cheetah
2.Fresh install: 
# Follow the installation steps above again
# Remember to:
# - Recreate your .env file
# - Re-add bot as admin to your channel
3.verify running status
tmux attach -t cheetah_bot  # Should show bot is running
4.check logs
tail -n 50 nohup.out  # Or your log file



##can be deployed on koyeb,heroku,vps,termux,etc
🚀 Termux Deployment Guide
# 1. UPDATE SYSTEM & INSTALL ESSENTIALS
pkg update -y && pkg upgrade -y
pkg install -y python git libjpeg-turbo libcrypt clang ffmpeg

# 2. CONFIGURE PYTHON ENVIRONMENT
export CC=clang  # Faster compilation
python -m pip install --upgrade pip wheel

# 3. CLONE REPOSITORY
git clone https://github.com/Aryanwadhonkar/Cheetah.git
cd Cheetah

# 4. INSTALL REQUIREMENTS
pip install --no-cache-dir -r requirements.txt

# 5. SETUP ENVIRONMENT FILE
cat > .env <<EOF
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here
DB_CHANNEL_ID=-1001234567890  # With -100 prefix
ADMINS=123456789,987654321    # Your Telegram ID(s)
FORCE_JOIN=0                  # Optional channel ID
SHORTENER_API=your_key        # Optional
SHORTENER_DOMAIN=your.domain  # Optional
EOF

# 6. RUN THE BOT (PERSISTENT)
tmux new -s cheetah_bot
python main.py

# Press Ctrl+B then D to detach
🔍 Verification Steps
1.Check if bot is running:
tmux attach -t cheetah_bot
# Should see the ASCII art and "Bot started"
2.Test bot functionality:
Send /start to your bot in Telegram
Admins can test /getlink by replying to a file

⚠️ Troubleshooting
Issue.                             Solution
Missing dependencies.           Run pkg install libjpeg-turbo clang and reinstall requirements
FloodWait errors.               Increase REQUEST_DELAY in main.py (line 36)
Bot not responding.            Check logs with tail -n 50 nohup.out 
Termux closing bot.            Use termux-wake-lock before starting

🔄 Updating the Bot
1.For better performance:
export PYTHONOPTIMIZE=1  # Before starting bot
2.Auto-restart on crash (create start.sh):
#!/bin/bash
while true; do
    python main.py
    sleep 10
done
then run:
chmod +x start.sh
tmux new -s cheetah_bot ./start.sh
3.monitor resources usage:
watch -n 1 'ps -o pid,%cpu,%mem,cmd -C python'




