from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse
from app.core.dependencies import get_current_user
from app.schemas.quotes import FeedbackRequest, TTSRequest
from app.services.gcp import db
from app.services.quote_service import generate_quote_batch
from app.services.audio_service import generate_audio

router = APIRouter()

@router.get("/api/batch")
def api_get_batch(count: int = 3, user: dict = Depends(get_current_user)):
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    user_ref = db.collection("users").document(user["email"])
    profile, cards = generate_quote_batch(user_ref, user["name"], count=count)
    return {"streak": profile["streak"], "cards": cards}

@router.post("/api/tts")
def api_generate_tts(payload: TTSRequest, user: dict = Depends(get_current_user)):
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    user_ref = db.collection("users").document(user["email"])
    user_doc = user_ref.get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    preferred_voice = user_data.get("preferred_voice", "female")

    audio_url = generate_audio(payload.quote, user["name"], preferred_voice)
    if not audio_url:
        return JSONResponse({"error": "Failed to synthesize speech"}, status_code=500)

    if user_data.get("last_quote") == payload.quote:
        user_ref.set({"audio_url": audio_url}, merge=True)

    return {"audio_url": audio_url}

@router.post("/api/feedback")
def record_feedback(payload: FeedbackRequest, user: dict = Depends(get_current_user)):
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    user_ref = db.collection("users").document(user["email"])
    user_doc = user_ref.get()
    user_data = user_doc.to_dict() if user_doc.exists else {}

    if payload.action == "like" and payload.quote:
        liked = user_data.get("liked_quotes", [])
        if payload.quote not in liked:
            liked.append(payload.quote)
        user_ref.set({"liked_quotes": liked}, merge=True)
        return {"status": "liked", "total_likes": len(liked)}

    elif payload.action == "dislike" and payload.quote:
        disliked = user_data.get("disliked_quotes", [])
        if payload.quote not in disliked:
            disliked.append(payload.quote)
        user_ref.set({"disliked_quotes": disliked}, merge=True)
        return {"status": "disliked", "total_dislikes": len(disliked)}

    return {"status": "ignored"}

@router.post("/preferences")
def update_preferences(
    mood: str = Form(...),
    goal: str = Form(...),
    voice: str = Form(...),
    user: dict = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_ref = db.collection("users").document(user["email"])
    generate_quote_batch(
        user_ref,
        name=user["name"],
        count=1,
        mood=mood.strip(),
        goal=goal.strip(),
        voice=voice.strip()
    )
    return RedirectResponse(url="/app", status_code=303)