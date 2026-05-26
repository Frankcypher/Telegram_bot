import os
import time
import requests
import threading
from flask import Flask

# 1. Flask keep-alive for Render free tier
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot running"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))

# 2. Load from Render Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HF_TOKEN = os.getenv("HF_TOKEN")
VIDEO_FILE = os.getenv("VIDEO_FILE", "output.mp4")

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}
HF_API_URL = "https://api.inference.huggingface.co"
TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_tg(msg):
    try:
        r = requests.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10
        )
        print("Telegram:", r.status_code, r.text)
        return r.status_code == 200
    except Exception as e:
        print("Telegram send failed:", e)
        return False

def send_video_tg(filepath, caption=""):
    try:
        with open(filepath, 'rb') as f:
            r = requests.post(
                f"{TG_API}/sendVideo",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"video": f},
                timeout=120
            )
        print("Telegram video:", r.status_code)
        return r.status_code == 200
    except Exception as e:
        print("Telegram video send failed:", e)
        send_tg(f"❌ Failed to send video: {e}")
        return False

def generate_story():
    prompt = """Write a 40-second moral story for kids. 3-4 sentences max.
    Give a clear moral like honesty or kindness.
    Then give 1 line video prompt for AI video generation.

    Format:
    STORY: <story>
    PROMPT: <video prompt>"""

    url = f"{HF_API_URL}/models/mistralai/Mistral-7B-Instruct-v0.3"
    payload = {
        "inputs": f"[INST] {prompt} [/INST]",
        "parameters": {"max_new_tokens": 200, "temperature": 0.7}
    }

    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=60)
        r.raise_for_status()
        text = r.json()[0]["generated_text"]
        text = text.split("[/INST]")[-1].strip()
    except requests.exceptions.RequestException as e:
        err_text = r.text[:200] if 'r' in locals() else 'No response'
        send_tg(f"❌ Story API error: {e}\nHF Response: {err_text}")
        return None, None

    try:
        story = text.split("PROMPT:")[0].replace("STORY:", "").strip()
        video_prompt = text.split("PROMPT:")[1].strip()
    except IndexError:
        send_tg(f"❌ Parse error. Model output:\n{text}")
        return None, None

    with open("story.txt", "w", encoding="utf-8") as f:
        f.write(story)
    return story, video_prompt

def generate_video(prompt):
    print("Generating image...")
    send_tg("🎨 Generating image...")

    img_url = f"{HF_API_URL}/models/black-forest-labs/FLUX.1-schnell"
    img_payload = {"inputs": prompt}

    try:
        img = requests.post(img_url, headers=HEADERS, json=img_payload, timeout=120)
        img.raise_for_status()
        img_data = img.content
    except Exception as e:
        err_text = img.text[:200] if 'img' in locals() else 'No response'
        send_tg(f"❌ Image API error: {e}\nHF Response: {err_text}")
        return False

    with open("frame.png", "wb") as f:
        f.write(img_data)

    print("Animating to video...")
    send_tg("🎬 Animating to video...")

    vid_url = f"{HF_API_URL}/models/stabilityai/stable-video-diffusion-img2vid-xt"
    try:
        with open("frame.png", "rb") as f:
            files = {"image": f}
            vid = requests.post(vid_url, headers=HEADERS, files=files, timeout=180)
            vid.raise_for_status()
            vid_data = vid.content
    except Exception as e:
        err_text = vid.text[:200] if 'vid' in locals() else 'No response'
        send_tg(f"❌ Video API error: {e}\nHF Response: {err_text}")
        return False

    with open(VIDEO_FILE, "wb") as f:
        f.write(vid_data)

    print(f"Video saved as {VIDEO_FILE}")
    return True

def main_loop():
    send_tg("🤖 Bot started on Render")
    while True:
        try:
            story, video_prompt = generate_story()
            if not story:
                time.sleep(300)
                continue

            send_tg(f"📖 Story:\n{story}")
            success = generate_video(video_prompt)

            if success and os.path.exists(VIDEO_FILE):
                send_tg("📤 Sending video...")
                send_video_tg(VIDEO_FILE, caption=story[:200])
            else:
                send_tg("❌ Video generation failed")

            time.sleep(3600)

        except Exception as e:
            send_tg(f"❌ Unexpected error: {e}")
            time.sleep(300)

if __name__ == "__main__":
    print("Starting bot...")

    # Run the bot loop in background thread
    threading.Thread(target=main_loop, daemon=True).start()

    # Run Flask in main thread so Render keeps it alive
    run_flask()
