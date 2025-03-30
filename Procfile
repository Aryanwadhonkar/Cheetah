# Universal Procfile for all platforms
# -----------------------------------
worker: python main.py
web: python main.py
release: python -c "print('Release phase completed')" || true
healthcheck: curl -f http://localhost:$PORT/healthcheck || exit 1

#In your Python code, add this basic healthcheck endpoint (optional but recommended):
#@app.on_message(filters.command("healthcheck"))
#async def health_check(client, message):
#await message.reply("OK")

#To deoloy
# Just push to your platform - no other commands needed
#git push heroku main  # or push to Koyeb/Railway/etc.
