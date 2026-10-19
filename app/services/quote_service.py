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
    voice: str = None,
    language: str = None
):
    """Generates a batch of N personalized quotes WITHOUT upfront TTS cost."""
    user_doc = user_ref.get()
    user_data = user_doc.to_dict() if user_doc.exists else {}

    saved_goal = goal if goal else user_data.get("goal", "building great habits")
    saved_mood = mood if mood else user_data.get("last_mood", "focused")
    saved_voice = voice if voice else user_data.get("preferred_voice", "female")
    saved_language = language if language else user_data.get("language", "en")
    streak = user_data.get("streak", 0) + 1
    last_quote = user_data.get("last_quote", "")

    interests = user_data.get("interests", [])
    ai_persona_summary = user_data.get("ai_persona_summary", "")
    app_usage_context = user_data.get("app_usage_context", "")

    liked = user_data.get("liked_quotes", [])[-5:]
    disliked = user_data.get("disliked_quotes", [])[-5:]

    context_parts = []
    if interests:
        interests_str = ", ".join(interests) if isinstance(interests, list) else str(interests)
        context_parts.append(f"User Interests & Passions: {interests_str}. Weave relevant metaphors, imagery, and themes from these domains.")
    if ai_persona_summary:
        context_parts.append(f"User AI Persona Profile: '{ai_persona_summary}'. Align the coaching tone, intensity, and wisdom with this personality.")
    if app_usage_context:
        context_parts.append(f"Current User Activity Context: '{app_usage_context}'. Address their current headspace or focus.")
    if liked:
        context_parts.append(f"Quotes the user loved in the past (match tone/style): {liked}.")
    if disliked:
        context_parts.append(f"Quotes the user disliked in the past (avoid tone/style): {disliked}.")

    context_str = "\n".join(context_parts)
    if context_str:
        context_str = "\n" + context_str

    if saved_language == "te":
        prompt = (
            f"You are an inspiring, minimalist personal mindset coach fluent in Telugu. "
            f"Write {count} distinct, short, punchy 1-to-2 sentence motivational quotes for {name} in authentic, natural, inspiring Telugu script (తెలుగు). "
            f"Current mood: '{saved_mood}'. Main goal: '{saved_goal}'. "
            f"Do not repeat: '{last_quote}'.{context_str}\n"
            f"Return ONLY a JSON array of {count} strings written in Telugu script."
        )
        default_fallback = "ప్రతిరోజూ చేసే చిన్న ప్రయత్నాలే అద్భుతమైన విజయాలకు దారితీస్తాయి."
    else:
        prompt = (
            f"You are an insightful, minimalist personal coach. "
            f"Write {count} distinct, short, punchy 1-to-2 sentence motivational quotes for {name}. "
            f"Current mood: '{saved_mood}'. Main goal: '{saved_goal}'. "
            f"Do not repeat: '{last_quote}'.{context_str}\n"
            f"Return ONLY a JSON array of {count} strings."
        )
        default_fallback = "Small daily improvements over time lead to stunning results."

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
        quotes_list = [default_fallback]

    quotes_list = [str(q).strip().strip('"') for q in quotes_list[:count]]

    # Audio is empty initially; generated on-demand only when user clicks 🔊!
    cards = [{"quote": q, "audio_url": ""} for q in quotes_list]

    updated_profile = {
        "name": name,
        "goal": saved_goal,
        "last_mood": saved_mood,
        "preferred_voice": saved_voice,
        "language": saved_language,
        "streak": streak,
        "last_quote": cards[0]["quote"],
        "audio_url": "",  # Reset until user requests audio for this quote
        "liked_quotes": user_data.get("liked_quotes", []),
        "disliked_quotes": user_data.get("disliked_quotes", []),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    user_ref.set(updated_profile, merge=True)
    return updated_profile, cards