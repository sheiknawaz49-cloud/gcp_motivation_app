import uuid
import logging
from google.cloud import texttospeech
from app.core.config import settings
from app.services.gcp import tts_client, storage_client

logger = logging.getLogger("motivation-app")


def generate_audio(text: str, username: str, voice_gender: str = "female") -> str:
    """Converts quote text to a unique MP3 in Google Cloud Storage so prefetched clips don't overwrite each other."""
    if not tts_client or not storage_client:
        logger.warning("TTS or Storage client is not initialized.")
        return ""

    try:
        voice_name = settings.VOICE_MAP.get(voice_gender.lower(), "en-US-Journey-F")
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", name=voice_name
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
