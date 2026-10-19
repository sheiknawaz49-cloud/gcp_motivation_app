import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    PROJECT_ID: str = (
        os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("PROJECT_ID")
        or os.getenv("YOUR_PROJECT_ID")
        or "motivation-app101"
    )
    LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("LOCATION") or "us-central1"
    BUCKET_NAME: str = os.getenv("AUDIO_BUCKET_NAME") or os.getenv("BUCKET_NAME") or f"{PROJECT_ID}-audio"
    APP_PASSCODE: str = os.getenv("APP_PASSCODE") or "my-super-secret-123"
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
    GOOGLE_CLIENT_ID: str = (
        os.environ.get("GOOGLE_CLIENT_ID")
        or "714998427403-f264mm8gojrl312mmad5p8u84mr3lid2.apps.googleusercontent.com"
    )
    SECRET_KEY: str = os.environ.get("SECRET_KEY") or "nawaz@king"

    # Directory Paths
    APP_DIR: Path = Path(__file__).resolve().parent.parent
    TEMPLATES_DIR: Path = APP_DIR / "templates"
    STATIC_DIR: Path = APP_DIR / "static"

    # Audio voice settings
    VOICE_MAP: dict = {
        "female": "en-US-Journey-F",
        "male": "en-US-Journey-D"
    }

    COOKIE_MAX_AGE: int = 30 * 24 * 60 * 60  # 30 days in seconds


settings = Settings()
