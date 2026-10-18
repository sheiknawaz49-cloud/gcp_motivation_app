import os
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from google import genai
from google.cloud import firestore

# Configure standard Python logging (Cloud Run captures this automatically)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("motivation-app")

app = FastAPI()

# Replace with your actual GCP Project ID
PROJECT_ID = "motivation-app101"# os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_PROJECT_ID")
LOCATION = "us-central1"

ai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID)

@app.get("/")
def home():
    return {"status": "healthy", "message": "Motivation API is live! Visit /app/YourName for the UI."}

@app.get("/motivate/{name}")
def get_motivation(name: str, mood: str = "focused", goal: str = None):
    logger.info(f"Generating motivation for user='{name}', mood='{mood}'")
    try:
        user_ref = db.collection("users").document(name.lower())
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            saved_goal = goal if goal else user_data.get("goal", "building my first cloud app")
            streak = user_data.get("streak", 0) + 1
            last_quote = user_data.get("last_quote", "")
        else:
            saved_goal = goal if goal else "building my first cloud app"
            streak = 1
            last_quote = ""

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

        updated_profile = {
            "name": name,
            "goal": saved_goal,
            "last_mood": mood,
            "streak": streak,
            "last_quote": new_quote,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        user_ref.set(updated_profile)

        logger.info(f"Successfully updated streak to {streak} for user='{name}'")
        return {
            "user": name,
            "check_in_streak": streak,
            "saved_goal": saved_goal,
            "current_mood": mood,
            "motivation": new_quote
        }

    except Exception as e:
        logger.error(f"Error generating motivation for {name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Something went wrong generating your quote.")

@app.get("/app/{name}", response_class=HTMLResponse)
def web_ui(name: str, mood: str = "focused", goal: str = None):
    """A clean, mobile-friendly HTML page for your Motivation App."""
    data = get_motivation(name=name, mood=mood, goal=goal)
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{data['user']}'s Daily Motivation</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
            .card {{ background: #1e293b; padding: 32px; border-radius: 16px; max-width: 480px; width: 100%; box-shadow: 0 10px 25px rgba(0,0,0,0.4); }}
            .badge {{ background: #3b82f6; color: white; padding: 6px 12px; border-radius: 999px; font-size: 14px; font-weight: bold; display: inline-block; margin-bottom: 16px; }}
            h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
            .meta {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
            .quote {{ font-size: 18px; line-height: 1.6; background: #0f172a; padding: 20px; border-left: 4px solid #3b82f6; border-radius: 8px; margin-bottom: 24px; }}
            form {{ display: flex; flex-direction: column; gap: 12px; }}
            input {{ padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; font-size: 14px; }}
            button {{ background: #10b981; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }}
            button:hover {{ background: #059669; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">🔥 Streak: {data['check_in_streak']}</div>
            <h1>Hey, {data['user']}!</h1>
            <div class="meta">🎯 Goal: <b>{data['saved_goal']}</b> | 🧠 Mood: <b>{data['current_mood']}</b></div>
            <div class="quote">"{data['motivation']}"</div>
            <form method="get" action="/app/{data['user']}">
                <input type="text" name="mood" placeholder="Update mood (e.g., tired, hyped, curious)" required />
                <input type="text" name="goal" placeholder="Update goal (optional)" />
                <button type="submit">Get Fresh Motivation ✨</button>
            </form>
        </div>
    </body>
    </html>
    """