import os
import time
import requests
from flask import Flask
import telebot
from threading import Thread

# Load env vars
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HF_TOKEN = os.getenv("HF_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

HF_API_URL = "https://api-inference.huggingface.co/models/damo-vilab/text-to-video-ms-1.7b"

@app.route("/")
def home():
    return "Bot is running"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Bot online ✅ Send /video <prompt> to generate a video")

@bot.message_handler(commands=['video'])
def handle_video(message):
    prompt = message.text.replace('/video', '').strip()
    if not prompt:
        bot.reply_to(message, "Send it like: /video a cat running in space")
        return
    
    bot.reply_to(message, "🎬 Generating video... this takes 30-90s")
    
    try:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs": prompt}
        
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=180)
        
        if response.status_code == 200:
            with open("video.mp4", "wb") as f:
                f.write(response.content)
            with open("video.mp4", "rb") as vid:
                bot.send_video(message.chat.id, vid)
            os.remove("video.mp4")
        else:
            bot.reply_to(message, f"Error {response.status_code}: {response.text[:200]}")
            
    except Exception as e:
        bot.reply_to(message, f"Failed: {e}")

def run_bot():
    try:
        bot.send_message(int(CHAT_ID), "✅ Bot connected to Render and running!")
        print("Startup message sent")
    except Exception as e:
        print("Failed to send startup message:", e)
    
    bot.polling(none_stop=True, interval=1, drop_pending_updates=True)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    Thread(target=run_bot).start()
    run_flask()
