import json
import logging
from datetime import datetime, timezone
from google.genai import types
from app.services.gcp import ai_client

logger = logging.getLogger("motivation-app")

def generate_quote_batch(
    user_ref,
    name: str,
    count: int = 3,
    mood: str = None,
    goal: str = None,
    voice: str = None
):
    """Generates a batch of N personalized quotes WITHOUT upfront TTS cost."""
    user_doc = user_ref.get()
    user_data = user_doc.to_dict() if user_doc.exists else {}

    saved_goal = goal if goal else user_data.get("goal", "building great habits")
    saved_mood = mood if mood else user_data.get("last_mood", "focused")
    saved_voice = voice if voice else user_data.get("preferred_voice", "female")
    streak = user_data.get("streak", 0) + 1
    last_quote = user_data.get("last_quote", "")

    liked = user_data.get("liked_quotes", [])[-5:]
    disliked = user_data.get("disliked_quotes", [])[-5:]

    taste_context = ""
    if liked:
        taste_context += f"\nThe user LOVED these past quotes (match this tone/style): {liked}."
    if disliked:
        taste_context += f"\nThe user DISLIKED these past quotes (avoid this tone/style): {disliked}."

    prompt = (
        f"You are an insightful, minimalist personal coach. "
        f"Write {count} distinct, short, punchy 1-to-2 sentence motivational quotes for {name}. "
        f"Current mood: '{saved_mood}'. Main goal: '{saved_goal}'. "
        f"Do not repeat: '{last_quote}'. {taste_context} "
        f"Return ONLY a JSON array of {count} strings."
    )

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        quotes_list = json.loads(response.text)
        if not isinstance(quotes_list, list) or not quotes_list:
            quotes_list = [response.text.strip().strip('"')]
    except Exception as e:
        logger.error(f"Batch AI generation error: {e}")
        quotes_list = ["Small daily improvements over time lead to stunning results."]

    quotes_list = [str(q).strip().strip('"') for q in quotes_list[:count]]

    # Audio is empty initially; generated on-demand only when user clicks 🔊!
    cards = [{"quote": q, "audio_url": ""} for q in quotes_list]

    updated_profile = {
        "name": name,
        "goal": saved_goal,
        "last_mood": saved_mood,
        "preferred_voice": saved_voice,
        "streak": streak,
        "last_quote": cards[0]["quote"],
        "audio_url": "",  # Reset until user requests audio for this quote
        "liked_quotes": user_data.get("liked_quotes", []),
        "disliked_quotes": user_data.get("disliked_quotes", []),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    user_ref.set(updated_profile)
    return updated_profile, cards