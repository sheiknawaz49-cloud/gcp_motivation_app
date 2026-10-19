import uuid
import logging
from google.cloud import texttospeech
from app.core.config import settings
from app.services.gcp import tts_client, storage_client

logger = logging.getLogger("motivation-app")


VOICE_CONFIG = {
    "en": {
        "female": "en-US-Journey-F",
        "male": "en-US-Journey-D",
        "language_code": "en-US",
    },
    "te": {
        "female": "te-IN-Standard-A",
        "male": "te-IN-Standard-B",
        "language_code": "te-IN",
    },
}


def generate_audio(
    text: str,
    username: str,
    voice_gender: str = "female",
    language: str = "en"
) -> str:
    """Converts quote text to a unique MP3 in Google Cloud Storage with multi-lingual voice support."""
    if not tts_client or not storage_client:
        logger.warning("TTS or Storage client is not initialized.")
        return ""

    try:
        lang_key = "te" if language and language.strip().lower().startswith("te") else "en"
        cfg = VOICE_CONFIG.get(lang_key, VOICE_CONFIG["en"])
        voice_gender_clean = (voice_gender or "female").lower()
        voice_name = cfg.get(voice_gender_clean, cfg["female"])
        lang_code = cfg["language_code"]

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code, name=voice_name
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        bucket = storage_client.bucket(settings.BUCKET_NAME)
        clip_id = uuid.uuid4().hex[:8]
        blob_name = f"{username.lower()}_{clip_id}.mp3"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(tts_response.audio_content, content_type="audio/mpeg")
        return f"https://storage.googleapis.com/{settings.BUCKET_NAME}/{blob_name}"
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        return ""
