import logging
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.core.dependencies import create_session_cookie
from app.services.user_service import UserService

logger = logging.getLogger("motivation-app")
router = APIRouter()
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = None):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "google_client_id": settings.GOOGLE_CLIENT_ID,
            "error": error
        }
    )

@router.post("/auth/google")
def google_auth_callback(credential: str = Form(...)):
    """Verifies the Google ID token returned by the 'Sign in with Google' button."""
    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        email = idinfo["email"].lower()
        name = idinfo.get("given_name") or idinfo.get("name") or email.split("@")[0]
        picture = idinfo.get("picture", "")

        # Create or update user's Firestore profile keyed by their unique email
        UserService.init_google_user(email=email, name=name, picture=picture)

        # Set 30-day signed session cookie
        token = create_session_cookie(email=email, name=name, picture=picture)
        response = RedirectResponse(url="/app", status_code=303)
        response.set_cookie(
            key="session_token",
            value=token,
            max_age=30 * 24 * 60 * 60,
            httponly=True,
            samesite="lax"
        )
        return response

    except Exception as e:
        logger.error(f"Google Sign-In verification failed: {e}")
        return RedirectResponse(
            url="/login?error=Google+Sign-In+failed.+Please+try+again.",
            status_code=303
        )

@router.post("/login")
def login_submit(
    username: str = Form(...),
    passcode: str = Form(...)
):
    if passcode != settings.APP_PASSCODE:
        return RedirectResponse(
            url="/login?error=Invalid+passcode.+Please+try+again.",
            status_code=303
        )

    clean_user = username.strip()
    email = clean_user.lower()
    name = clean_user.capitalize()

    UserService.init_passcode_user(email=email, name=name)

    token = create_session_cookie(email=email, name=name, picture="")
    response = RedirectResponse(url="/app", status_code=303)
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        samesite="lax"
    )
    return response

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response