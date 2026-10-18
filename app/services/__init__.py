"""
Service layer for GCP clients, audio generation, quote logic, and user persistence.
"""
from app.services.audio_service import generate_audio
from app.services.quote_service import generate_quote_batch
from app.services.user_service import UserService

__all__ = ["generate_audio", "generate_quote_batch", "UserService"]
