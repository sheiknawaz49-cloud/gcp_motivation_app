import logging
from google import genai
from google.cloud import firestore
from google.cloud import texttospeech
from google.cloud import storage
from app.core.config import settings

logger = logging.getLogger("motivation-app")

try:
    ai_client = genai.Client(
        vertexai=True,
        project=settings.PROJECT_ID,
        location=settings.LOCATION
    )
except Exception as e:
    logger.error(f"Failed to initialize Google GenAI Client: {e}")
    ai_client = None

try:
    db = firestore.Client(project=settings.PROJECT_ID)
except Exception as e:
    logger.error(f"Failed to initialize Firestore Client: {e}")
    db = None

try:
    tts_client = texttospeech.TextToSpeechClient()
except Exception as e:
    logger.error(f"Failed to initialize Text-to-Speech Client: {e}")
    tts_client = None

try:
    storage_client = storage.Client(project=settings.PROJECT_ID)
except Exception as e:
    logger.error(f"Failed to initialize Storage Client: {e}")
    storage_client = None
