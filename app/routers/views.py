import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.services.user_service import UserService
from app.services.quote_service import generate_quote_batch

logger = logging.getLogger("motivation-app")
router = APIRouter()
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

@router.get("/")
def home(user: dict = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/app")
    return {"status": "healthy", "message": "Visit /app to sign in with Google."}

@router.get("/onboarding", response_class=HTMLResponse)
def onboarding_ui(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    email = user["email"]
    name = user["name"]
    user_data = UserService.get_user_data(email)

    saved_interests = user_data.get("interests", [])
    saved_persona = user_data.get("ai_persona_summary", "")
    saved_language = user_data.get("language", "en")

    return templates.TemplateResponse(
        request=request,
        name="onboarding.html",
        context={
            "session_user": name,
            "user_picture": user.get("picture", ""),
            "saved_interests": saved_interests,
            "saved_persona": saved_persona,
            "saved_language": saved_language
        }
    )

@router.post("/onboarding")
async def onboarding_submit(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    form_data = await request.form()
    interests = form_data.getlist("interests")
    ai_persona_summary = str(form_data.get("ai_persona_summary", "")).strip()
    language = str(form_data.get("language", "en")).strip().lower()
    if language != "te":
        language = "en"

    email = user["email"]
    name = user["name"]

    UserService.save_onboarding(
        email=email,
        name=name,
        picture=user.get("picture", ""),
        interests=interests,
        ai_persona_summary=ai_persona_summary,
        language=language
    )

    # Immediately regenerate personalized quote matching the new context & language
    try:
        user_ref = UserService.get_user_ref(email)
        generate_quote_batch(user_ref, name=name, count=1, language=language)
    except Exception as e:
        logger.error(f"Error generating post-onboarding quote: {e}")

    return RedirectResponse(url="/app", status_code=303)

@router.get("/onboarding/skip")
def onboarding_skip(user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    email = user["email"]
    name = user["name"]
    UserService.skip_onboarding(email=email, name=name)
    return RedirectResponse(url="/app", status_code=303)

@router.get("/app", response_class=HTMLResponse)
def minimal_app_ui(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    email = user["email"]
    name = user["name"]
    user_data = UserService.get_user_data(email)

    # If user has not completed or skipped onboarding, redirect to /onboarding
    if not user_data.get("onboarded", False):
        return RedirectResponse(url="/onboarding", status_code=303)

    user_ref = UserService.get_user_ref(email)
    if not user_data.get("last_quote"):
        data, _ = generate_quote_batch(
            user_ref,
            name,
            count=1,
            language=user_data.get("language", "en")
        )
    else:
        data = user_data

    saved_voice = data.get("preferred_voice", "female")
    voice_badge = "👩 Female" if saved_voice == "female" else "👨 Male"
    saved_language = data.get("language", "en")
    lang_badge = "🇮🇳 తెలుగు" if saved_language == "te" else "🇬🇧 EN"

    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={
            "session_user": name,
            "user_picture": user.get("picture", ""),
            "quote_text": data.get("last_quote", ""),
            "audio_url": data.get("audio_url", ""),
            "streak": data.get("streak", 1),
            "saved_goal": data.get("goal", "Daily growth"),
            "saved_mood": data.get("last_mood", "focused"),
            "saved_voice": saved_voice,
            "voice_badge": voice_badge,
            "saved_language": saved_language,
            "lang_badge": lang_badge
        }
    )