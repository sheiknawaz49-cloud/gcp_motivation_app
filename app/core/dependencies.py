from typing import Optional
from fastapi import Cookie, HTTPException, status
from app.core.config import settings


def get_current_user_optional(
    session_user: Optional[str] = Cookie(default=None),
    session_token: Optional[str] = Cookie(default=None)
) -> Optional[str]:
    """Returns the authenticated username if session is valid, else None."""
    if session_user and session_token == settings.APP_PASSCODE:
        return session_user.strip()
    return None


def get_current_user_api(
    session_user: Optional[str] = Cookie(default=None),
    session_token: Optional[str] = Cookie(default=None)
) -> str:
    """Dependency for API routes that raises 401 if unauthorized."""
    user = get_current_user_optional(session_user, session_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )
    return user
