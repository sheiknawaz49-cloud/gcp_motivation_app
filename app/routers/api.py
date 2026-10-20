from typing import Optional
from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse
from app.core.dependencies import get_current_user
from app.schemas.quotes import FeedbackRequest, TTSRequest, MobileContextRequest
from app.services.user_service import UserService
from app.services.quote_service import generate_quote_batch
from app.services.audio_service import generate_audio

router = APIRouter()

@router.get("/api/batch")
def api_get_batch(count: int = 3, user: dict = Depends(get_current_user)):
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    email = user["email"]
    user_ref = UserService.get_user_ref(email)
    user_data = UserService.get_user_data(email)

    daily_count, daily_cards, _ = UserService.get_daily_status(user_data)
    streak, max_streak, _ = UserService.calculate_streak(user_data)
    remaining = max(0, 3 - daily_count)

    if remaining == 0:
        return {
            "limit_reached": True,
            "remaining": 0,
            "streak": streak,
            "cards": [],
            "daily_cards": daily_cards
        }

    actual_to_generate = min(count, remaining)
    profile, new_cards = generate_quote_batch(user_ref, user["name"], count=actual_to_generate)
    return {
        "limit_reached": profile.get("daily_count", 0) >= 3,
        "remaining": max(0, 3 - profile.get("daily_count", 0)),
        "streak": profile.get("streak", streak),
        "cards": new_cards,
        "daily_cards": profile.get("daily_cards", daily_cards)
    }

@router.post("/api/tts")
def api_generate_tts(payload: TTSRequest, user: dict = Depends(get_current_user)):
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    email = user["email"]
    user_data = UserService.get_user_data(email)
    preferred_voice = user_data.get("preferred_voice", "female")
    saved_language = user_data.get("language", "en")

    audio_url = generate_audio(
        payload.quote,
        user["name"],
        preferred_voice,
        language=saved_language
    )
    if not audio_url:
        return JSONResponse({"error": "Failed to synthesize speech"}, status_code=500)

    # Cache audio URL in profile and daily_cards
    update_dict = {}
    if user_data.get("last_quote") == payload.quote:
        update_dict["audio_url"] = audio_url

    daily_cards = user_data.get("daily_cards", [])
    updated = False
    for card in daily_cards:
        if isinstance(card, dict) and card.get("quote") == payload.quote:
            card["audio_url"] = audio_url
            updated = True
    if updated:
        update_dict["daily_cards"] = daily_cards

    if update_dict:
        UserService.update_user(email, update_dict)

    return {"audio_url": audio_url}

@router.post("/api/feedback")
def record_feedback(payload: FeedbackRequest, user: dict = Depends(get_current_user)):
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    return UserService.record_feedback(user["email"], payload.action, payload.quote)

@router.post("/preferences")
def update_preferences(
    mood: str = Form(...),
    goal: str = Form(...),
    voice: str = Form(...),
    language: str = Form("en"),
    theme_mode: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    clean_lang = "te" if language and language.strip().lower() == "te" else "en"
    clean_mood = mood.strip()
    clean_goal = goal.strip()
    clean_voice = voice.strip()
    email = user["email"]

    pref_updates = {
        "mood": clean_mood,
        "last_mood": clean_mood,
        "goal": clean_goal,
        "preferred_voice": clean_voice,
        "language": clean_lang
    }
    if theme_mode:
        clean_theme = theme_mode.strip().lower()
        if clean_theme in ("auto", "light", "dark"):
            pref_updates["theme_mode"] = clean_theme

    # Always save the new preferences to Firestore
    UserService.update_user(email, pref_updates)

    # But ONLY generate a new quote if daily_count < 3
    user_data = UserService.get_user_data(email)
    daily_count, _, _ = UserService.get_daily_status(user_data)

    if daily_count < 3:
        user_ref = UserService.get_user_ref(email)
        generate_quote_batch(
            user_ref,
            name=user["name"],
            count=1,
            mood=clean_mood,
            goal=clean_goal,
            voice=clean_voice,
            language=clean_lang
        )

    return RedirectResponse(url="/app", status_code=303)

@router.post("/api/context/mobile")
def update_mobile_context(payload: MobileContextRequest, user: dict = Depends(get_current_user)):
    """Receives screen-time or app usage context from mobile apps/shortcuts and saves to user profile."""
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    clean_context = payload.app_usage_context.strip()
    UserService.update_mobile_context(user["email"], clean_context)
    return {
        "status": "success",
        "message": "Mobile context recorded successfully",
        "app_usage_context": clean_context
    }