import time, requests, os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Load from Render Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HF_TOKEN = os.getenv("HF_TOKEN")
VIDEO_FILE = os.getenv("VIDEO_FILE", "output.mp4")

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}
HF_API_URL = "https://api.inference.huggingface.co"
TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_tg(msg):
    try:
        r = requests.post(f"{TG_API}/sendMessage",
                         json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
                         timeout=10)
        print("Telegram:", r.status_code, r.text)
        return r.status_code == 200
    except Exception as e:
        print("Telegram send failed:", e)
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

    open("story.txt", "w", encoding="utf-8").write(story)
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
            data = {"motion_bucket_id": 127, "fps": 6}
            r = requests.post(vid_url, headers=HEADERS, files=files, data=data, timeout=300)
        r.raise_for_status()
    except Exception as e:
        err_text = r.text[:200] if 'r' in locals() else 'No response'
        send_tg(f"❌ Video API error: {e}\nHF Response: {err_text}")
        return False

    with open(VIDEO_FILE, "wb") as f:
        f.write(r.content)

    send_tg("✅ Video ready")
    return True

if __name__ == "__main__":
    send_tg("Bot started on Render")
    story, prompt = generate_story()
    if story and prompt:
        generate_video(prompt)
