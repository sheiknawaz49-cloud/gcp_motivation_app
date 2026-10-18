from typing import Optional
from fastapi import APIRouter, Depends, Form, Cookie, Request
from fastapi.responses import RedirectResponse, JSONResponse
from app.core.dependencies import get_current_user_api, get_current_user_optional
from app.services.user_service import UserService
from app.services.quote_service import generate_quote_batch

router = APIRouter(tags=["Quotes & Preferences"])


@router.get("/api/batch")
def api_get_batch(
    count: int = 3,
    current_user: str = Depends(get_current_user_api)
):
    """Returns a batch of quotes + audio URLs so the client can display upcoming cards instantly."""
    user_ref = UserService.get_user_ref(current_user)
    profile, cards = generate_quote_batch(user_ref, current_user, count=count)
    return {"streak": profile["streak"], "cards": cards}


@router.post("/preferences")
def update_preferences(
    mood: str = Form(...),
    goal: str = Form(...),
    voice: str = Form(...),
    session_user: Optional[str] = Cookie(default=None),
    session_token: Optional[str] = Cookie(default=None)
):
    """Updates the user's coaching preferences and refreshes the current deck."""
    user = get_current_user_optional(session_user, session_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_ref = UserService.get_user_ref(user)
    generate_quote_batch(
        user_ref,
        name=user,
        count=1,
        mood=mood.strip(),
        goal=goal.strip(),
        voice=voice.strip()
    )
    return RedirectResponse(url="/app", status_code=303)


@router.post("/api/feedback")
async def record_feedback(
    request: Request,
    current_user: str = Depends(get_current_user_api)
):
    """Records like/dislike taste feedback to personalize future quote recommendations."""
    body = await request.json()
    action = body.get("action")
    quote = body.get("quote", "")

    result = UserService.record_feedback(current_user, action, quote)
    return JSONResponse(result)
