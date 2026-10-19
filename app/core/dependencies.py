import hmac
import hashlib
import base64
import json
from typing import Optional, Dict
from fastapi import Cookie
from app.core.config import settings

def create_session_cookie(email: str, name: str, picture: str = "") -> str:
    """Creates a tamper-proof signed session token containing user info."""
    payload = json.dumps({"email": email.lower(), "name": name, "picture": picture})
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{payload_b64}.{signature}"

def get_current_user(session_token: Optional[str] = Cookie(default=None)) -> Optional[Dict[str, str]]:
    """Verifies the signed session cookie and returns {"email": ..., "name": ..., "picture": ...}."""
    if not session_token or "." not in session_token:
        return None
    try:
        payload_b64, signature = session_token.rsplit(".", 1)
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        return payload
    except Exception:
        return None

