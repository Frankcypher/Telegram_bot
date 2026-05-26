import os
import time
import requests
import threading
import telebot
from flask import Flask

# Load env vars
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HF_TOKEN = os.getenv("HF_TOKEN")

print("Token loaded:", BOT_TOKEN[:10] if BOT_TOKEN else "None", "...")
print("Chat ID loaded:", CHAT_ID if CHAT_ID else "None")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Bot is live on Render 🚀")

def run_bot():
    try:
        bot.send_message(int(CHAT_ID), "✅ Bot connected to Render and running!")
        print("Startup message sent")
    except Exception as e:
        print("Failed to send startup message:", e)
    
    bot.polling(none_stop=True, interval=1)

if __name__ == "__main__":
    # Run bot in background thread so Flask can handle health checks
    threading.Thread(target=run_bot).start()
    
    # Run Flask for Render
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
