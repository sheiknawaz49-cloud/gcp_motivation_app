from typing import Optional
from fastapi import APIRouter, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.core.dependencies import get_current_user_optional
from app.services.user_service import UserService
from app.services.quote_service import generate_quote_batch

router = APIRouter(tags=["Views"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/")
def home(
    session_user: Optional[str] = Cookie(default=None),
    session_token: Optional[str] = Cookie(default=None)
):
    """Health check / landing router redirecting authenticated users to /app."""
    user = get_current_user_optional(session_user, session_token)
    if user:
        return RedirectResponse(url="/app")
    return {"status": "healthy", "message": "Visit /app to log in and view your quotes."}


@router.get("/app", response_class=HTMLResponse)
def minimal_app_ui(
    request: Request,
    session_user: Optional[str] = Cookie(default=None),
    session_token: Optional[str] = Cookie(default=None)
):
    """Main interactive motivation quote card view."""
    user = get_current_user_optional(session_user, session_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_ref = UserService.get_user_ref(user)
    user_data = UserService.get_user_data(user)

    if not user_data or not user_data.get("last_quote"):
        data, _ = generate_quote_batch(user_ref, user, count=1)
    else:
        data = user_data

    quote_text = data.get("last_quote", "")
    audio_url = data.get("audio_url", "")
    streak = data.get("streak", 1)
    saved_goal = data.get("goal", "Daily growth")
    saved_mood = data.get("last_mood", "focused")
    saved_voice = data.get("preferred_voice", "female")

    female_selected = "selected" if saved_voice == "female" else ""
    male_selected = "selected" if saved_voice == "male" else ""
    voice_badge = "👩 Female" if saved_voice == "female" else "👨 Male"

    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={
            "session_user": user,
            "quote_text": quote_text,
            "audio_url": audio_url,
            "streak": streak,
            "saved_goal": saved_goal,
            "saved_mood": saved_mood,
            "saved_voice": saved_voice,
            "voice_badge": voice_badge,
            "female_selected": female_selected,
            "male_selected": male_selected
        }
    )
