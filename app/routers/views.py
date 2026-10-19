from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.services.gcp import db
from app.services.quote_service import generate_quote_batch

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

@router.get("/")
def home(user: dict = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/app")
    return {"status": "healthy", "message": "Visit /app to sign in with Google."}

@router.get("/app", response_class=HTMLResponse)
def minimal_app_ui(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    email = user["email"]
    name = user["name"]
    user_ref = db.collection("users").document(email)
    user_doc = user_ref.get()

    if not user_doc.exists or not user_doc.to_dict().get("last_quote"):
        data, _ = generate_quote_batch(user_ref, name, count=1)
    else:
        data = user_doc.to_dict()

    saved_voice = data.get("preferred_voice", "female")
    voice_badge = "👩 Female" if saved_voice == "female" else "👨 Male"

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
            "voice_badge": voice_badge
        }
    )