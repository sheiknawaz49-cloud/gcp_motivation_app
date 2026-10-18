import os
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from google import genai
from google.cloud import firestore
from google.cloud import texttospeech
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("motivation-app")

app = FastAPI()

# Replace with your actual GCP Project ID
PROJECT_ID = "motivation-app101"# os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_PROJECT_ID")
LOCATION = "us-central1"
BUCKET_NAME = f"{PROJECT_ID}-audio"

APP_PASSCODE = 'my-super-secret-123'#os.environ.get("APP_PASSCODE", "local-dev-passcode")

# Initialize GCP Clients
ai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID)
tts_client = texttospeech.TextToSpeechClient()
storage_client = storage.Client(project=PROJECT_ID)

def generate_audio(text: str, username: str) -> str:
    """Converts quote text to MP3 and uploads to Google Cloud Storage."""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Journey-D"  # Expressive, natural-sounding Google AI voice
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    tts_response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Upload MP3 bytes to Google Cloud Storage
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"{username.lower()}_latest.mp3")
    blob.upload_from_string(tts_response.audio_content, content_type="audio/mpeg")
    blob.cache_control = "no-cache, max-age=0"
    blob.patch()

    return f"https://storage.googleapis.com/{BUCKET_NAME}/{username.lower()}_latest.mp3?t={int(datetime.now().timestamp())}"

@app.get("/")
def home():
    return {"status": "healthy", "message": "Visit /app/YourName for the Voice-Enabled UI."}

@app.get("/motivate/{name}")
def get_motivation(name: str, mood: str = "focused", goal: str = None, code: str = None):
    user_ref = db.collection("users").document(name.lower())
    user_doc = user_ref.get()
    user_data = user_doc.to_dict() if user_doc.exists else {}

    if code != APP_PASSCODE:
        return {
            "user": name,
            "check_in_streak": user_data.get("streak", 0),
            "saved_goal": user_data.get("goal", "Set your first goal below!"),
            "current_mood": user_data.get("last_mood", mood),
            "motivation": user_data.get("last_quote", "🔒 Enter your secret passcode below to generate a fresh AI quote!"),
            "audio_url": user_data.get("audio_url", ""),
            "auth_status": "🔒 Locked (Read-Only)" if code is None else "❌ Wrong Passcode!"
        }

    saved_goal = goal if goal else user_data.get("goal", "building my first cloud app")
    streak = user_data.get("streak", 0) + 1
    last_quote = user_data.get("last_quote", "")

    prompt = (
        f"You are an energetic, practical personal coach. "
        f"Write a short, punchy 2-sentence motivational message for {name}. "
        f"This is their check-in #{streak}. "
        f"Right now they are feeling '{mood}' and their main goal is '{saved_goal}'. "
        f"Do not repeat this previous message: '{last_quote}'. "
        f"Keep it grounded, personal, and actionable."
    )

    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    new_quote = response.text.strip()

    # Generate MP3 voice clip and store in Cloud Storage
    audio_url = generate_audio(new_quote, name)

    updated_profile = {
        "name": name,
        "goal": saved_goal,
        "last_mood": mood,
        "streak": streak,
        "last_quote": new_quote,
        "audio_url": audio_url,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    user_ref.set(updated_profile)

    return {
        "user": name,
        "check_in_streak": streak,
        "saved_goal": saved_goal,
        "current_mood": mood,
        "motivation": new_quote,
        "audio_url": audio_url,
        "auth_status": "✅ Secret Verified! Streak & Audio Updated"
    }

@app.get("/app/{name}", response_class=HTMLResponse)
def web_ui(name: str, mood: str = "focused", goal: str = None, code: str = None):
    data = get_motivation(name=name, mood=mood, goal=goal, code=code)
    status_color = "#10b981" if "✅" in data["auth_status"] else "#f59e0b"
    audio_html = f'<audio controls autoplay src="{data["audio_url"]}" style="width: 100%; margin-bottom: 24px;"></audio>' if data.get("audio_url") else ""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{data['user']}'s Daily Motivation</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
            .card {{ background: #1e293b; padding: 32px; border-radius: 16px; max-width: 480px; width: 100%; box-shadow: 0 10px 25px rgba(0,0,0,0.4); }}
            .badges {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }}
            .badge {{ background: #3b82f6; color: white; padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: bold; }}
            .status-badge {{ background: {status_color}; color: white; padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: bold; }}
            h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
            .meta {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
            .quote {{ font-size: 18px; line-height: 1.6; background: #0f172a; padding: 20px; border-left: 4px solid #3b82f6; border-radius: 8px; margin-bottom: 16px; }}
            form {{ display: flex; flex-direction: column; gap: 12px; }}
            input {{ padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; font-size: 14px; }}
            button {{ background: #10b981; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badges">
                <div class="badge">🔥 Streak: {data['check_in_streak']}</div>
                <div class="status-badge">{data['auth_status']}</div>
            </div>
            <h1>Hey, {data['user']}!</h1>
            <div class="meta">🎯 Goal: <b>{data['saved_goal']}</b> | 🧠 Mood: <b>{data['current_mood']}</b></div>
            <div class="quote">"{data['motivation']}"</div>
            {audio_html}
            <form method="get" action="/app/{data['user']}">
                <input type="text" name="mood" placeholder="Update mood (e.g., focused, hyped)" required />
                <input type="text" name="goal" placeholder="Update goal (optional)" />
                <input type="password" name="code" placeholder="Enter Secret Passcode" required />
                <button type="submit">Unlock Fresh Voice Motivation 🎧</button>
            </form>
        </div>
    </body>
    </html>
    """