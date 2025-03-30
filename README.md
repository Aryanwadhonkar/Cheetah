📁 Telegram File Store Bot
A powerful bot that stores files in a private channel and provides secure, time-limited access links. Perfect for sharing files with expiration and access control.

🌟 Features
🔒 Secure file storage in private channel

⏳ Auto-expiring access links (24 hours default)

🗑️ Auto-delete files from user chats (10 minutes default)

👮 Admin-only uploads

📤 Batch file uploads

📢 Broadcast messages to all users

🔗 URL shortener integration

🚦 Rate limiting for high traffic

💾 SQLite database for reliability

🛠️ Setup Guide
Prerequisites
Python 3.7+

Telegram API credentials

Termux (for Android installation)

Installation
1.Install requirements in Termux:
pkg update
pkg upgrade
pkg install python git sqlite
pip install pyrogram tgcrypto python-dotenv requests

2.Clone the repo
git clone https://github.com/yourusername/file-store-bot.git
cd file-store-bot

3.Set up environment variables:
Create a .env file with these values:

API_ID=1234567                          # From my.telegram.org
API_HASH=abcdef1234567890abcdef12345678  # From my.telegram.org
BOT_TOKEN=123456:ABC-DEF1234567890       # From @BotFather
DB_CHANNEL_ID=-1001234567890             # Your private channel ID
ADMINS=123456789,987654321               # Your admin user IDs
AUTO_DELETE_MINUTES=10                   # Auto-delete timer

🏗️ Configuration Explained
Variable	Description
API_ID	Get from my.telegram.org
API_HASH	Get from my.telegram.org
BOT_TOKEN	Get from @BotFather
DB_CHANNEL_ID	Create private channel, add bot as admin (include -100 prefix)
ADMINS	Your Telegram user ID(s), comma separated
AUTO_DELETE_MINUTES	Minutes until files auto-delete from user chats (0 to disable)
SHORTENER_API	(Optional) Your URL shortener API key
SHORTENER_DOMAIN	(Optional) Your shortener domain (e.g., example.com)

🚀 Running the Bot
python main.py

To run in background (Termux):
tmux new -s bot
python main.py
# Detach with Ctrl+B, then D


🤖 Bot Commands
For Admins
/upload - Store single file

/batch - Store multiple files

/broadcast - Message all users

/shortener - Configure URL shortener

For Users
/start - Get access token
/token - Generate new token



🔧 Troubleshooting
Common Issues:

Bot not responding:

Check if it's running in Termux (tmux attach -t bot)

Verify API credentials

Files not saving:

Ensure bot is admin in DB channel

Check channel ID includes -100 prefix

High memory usage:

Reduce MAX_CONCURRENT_DOWNLOADS in .env

Restart bot periodically



📜 License
MIT License - Free to use and modify

💡 Tip: For best performance on Android, close other apps while the bot is running!


🌐 Updated Hosting Guide with Docker Support


1. Docker Deployment (Works on All Platforms)
📝 Steps for Any Platform:
Build the image:
docker build -t file-store-bot .
Run the container
docker run -d \
  --name file-bot \
  -v ./data:/data \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e BOT_TOKEN=your_bot_token \
  -e DB_CHANNEL_ID=-1001234567890 \
  -e ADMINS=123456789 \
  file-store-bot




2. Heroku Deployment
   Add heroku.yml:
   build:
  docker:
    web: Dockerfile

   Deploy through Heroku CLI:
    heroku container:login
heroku container:push worker
heroku container:release worker



3.Koyeb with Docker
Create new app → Select "Docker"
Set image to yourusername/file-store-bot
Add all environment variables
Set volume mount: /data



4.VPS deployment through Docker
 # Install Docker
sudo apt update
sudo apt install docker.io docker-compose

# Create docker-compose.yml
version: '3.8'
services:
  bot:
    image: yourusername/file-store-bot
    restart: always
    volumes:
      - ./data:/data
    environment:
      - API_ID=your_api_id
      - API_HASH=your_api_hash
      - BOT_TOKEN=your_bot_token
      - DB_CHANNEL_ID=-1001234567890
      - ADMINS=123456789
      
# Start the bot
docker-compose up -d

🔧 Updated Environment Variables
Add these to your .env or Docker environment:
Variable	       Docker Example	         Description
DATABASE_PATH	   /data/filedb.db	       Path for SQLite database
WORKERS	         10	                     Number of concurrent workers
TZ	             UTC	                   Timezone for scheduling

🚀 Benefits of Docker Deployment
1.Consistency: Runs the same way everywhere
2.Isolation: No conflicts with other apps
3.Easy Updates:

docker-compose pull && docker-compose up -d --force-recreate

4.Resource Limits (add to compose file):
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M

      
📦 Docker-Specific Tips
1.For better performance
# Add to Dockerfile
RUN pip install uvloop

2.To check logs
docker logs -f file-bot

3.to update
docker-compose down
docker-compose pull
docker-compose up -d

"Choose Docker for the most reliable deployment across all platforms! The bot will maintain all its features while being more portable and easier to manage."
