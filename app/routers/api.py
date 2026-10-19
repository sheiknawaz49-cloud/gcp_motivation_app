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

    user_ref = UserService.get_user_ref(user["email"])
    profile, cards = generate_quote_batch(user_ref, user["name"], count=count)
    return {"streak": profile["streak"], "cards": cards}

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

    if user_data.get("last_quote") == payload.quote:
        UserService.update_user(email, {"audio_url": audio_url})

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
    user: dict = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    clean_lang = "te" if language and language.strip().lower() == "te" else "en"
    email = user["email"]
    UserService.set_language(email, clean_lang)

    user_ref = UserService.get_user_ref(email)
    generate_quote_batch(
        user_ref,
        name=user["name"],
        count=1,
        mood=mood.strip(),
        goal=goal.strip(),
        voice=voice.strip(),
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