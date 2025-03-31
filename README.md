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
Auto-delete          Files auto-delete after AUTO_DELETE minutes (configurable in .env).
URL Shortener	       Token links are shortened using shorten_url() (set API in .env).
Force-subscribe	     Users must join FORCE_SUB channel before using the bot.
24-hour Tokens	     Non-premium users get tokens that expire after 24 hours.
Premium Members	     Admins can whitelist users with /premium.
Admin Commands	     /broadcast, /ban, /stats, /restart, etc.
Credit Enforcement	 Bot crashes if credit is removed (check CREDIT variable).

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


📌 Pre-Deployment Checklist
Android Device: Redmi Note 12 Pro 5G (or any Android 10+)
Storage: Minimum 2GB free space
Internet: Stable connection (Wi-Fi recommended)
Termux: Latest version from F-Droid

🚀 Step 1: Setup Termux
pkg update -y && pkg upgrade -y
pkg install -y git python python-pip ffmpeg nano wget

termux-setup-storage #allow permission

cd ~/storage/shared
git clone https://github.com/Aryanwadhonkar/Cheetah
cd Cheetah

pip install -r requirements.txt

cp .env.example .env
nano .env
#Save with Ctrl+S → Exit with Ctrl+X

python main.py
#First run will ask for phone number and OTP (Telegram login)



⚙️Keep Bot Running 24/7
🐆Option A
  Just keep Termux open (not recommended long-term)

🐆Option B: Termux Boot (Auto-start)
   pkg install termux-boot
   mkdir -p ~/.termux/boot
   nano ~/.termux/boot/startbot
paste this:
   #!/data/data/com.termux/files/usr/bin/sh
   cd /storage/emulated/0/Cheetah
   python main.py
make it executable:
   chmod +x ~/.termux/boot/startbot

🐆Option C (Best):
   pkg install tmux
   tmux new -s cheetahbot
   cd ~/storage/shared/Cheetah
   python main.py

🔒 Step 4: Security & Maintenance.
  1.Protect Termux
    pkg install openssh
    passwd  # Set a strong password
    sshd    # Start SSH server

  2.Auto-Restart on crash:
      nano restart.sh
      
   paste this:
      #!/data/data/com.termux/files/usr/bin/sh
while true; do
    cd /storage/emulated/0/Cheetah
    python main.py
    sleep 10
done
   
   make executable:
    chmod +x restart.sh
    ./restart.sh

   3.Montitor bot logs
    tail -f ~/storage/shared/Cheetah/logs.txt

  
🌐 Step 5: Port Forwarding (Optional)
   If you want to expose bot APIs:
      pkg install cloudflared
      cloudflared tunnel --url http://localhost:8080
   
     Follow Cloudflare prompts to get a public URL

 💡 Troubleshooting
   1.Bot Not Starting?
     Check dependencies: pip list
     Verify API keys in .env
   2.Termux Closing?
     Disable battery optimization for Termmux Use tmux or termux-boot
   3.Storage Issues?
     termux-cleanup
     rm -rf ~/.cache

  📈 Advanced Optimization
    1.Reduce RAM Usage
        nano ~/.bashrc
    Add at the end:
        ulimit -Sv 500000  # Limit to 500MB hi RAM

   2. Scheduled Backups
      crontab -e
    Add (runs daily at 3 AM):
       0 3 * * * tar -czvf /storage/emulated/0/Cheetah_backup.tar.gz /storage/emulated/0/Cheetah

   ✅ Done!
      Your bot is now fully operational on Termux with:
      24/7 uptime (via tmux/termux-boot)
      Auto-restart on crashes
      File storage in private channels
  For updates:
      cd ~/storage/shared/Cheetah
      git pull
      python main.py
