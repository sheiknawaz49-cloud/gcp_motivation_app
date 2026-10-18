from typing import Optional
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.services.user_service import UserService

router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error}
    )


@router.post("/login")
def login_submit(
    username: str = Form(...),
    passcode: str = Form(...),
    goal: Optional[str] = Form(None),
    voice: str = Form("female")
):
    if passcode != settings.APP_PASSCODE:
        return RedirectResponse(
            url="/login?error=Invalid+passcode.+Please+try+again.",
            status_code=303
        )

    # Upsert user record in Firestore
    UserService.upsert_user(username, goal, voice)

    response = RedirectResponse(url="/app", status_code=303)
    response.set_cookie(
        key="session_user",
        value=username.strip(),
        max_age=settings.COOKIE_MAX_AGE,
        httponly=True
    )
    response.set_cookie(
        key="session_token",
        value=passcode,
        max_age=settings.COOKIE_MAX_AGE,
        httponly=True
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_user")
    response.delete_cookie("session_token")
    return response
