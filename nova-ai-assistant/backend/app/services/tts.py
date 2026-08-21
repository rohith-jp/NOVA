import httpx
import logging
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class TTSResult(BaseModel):
    audio_data: Optional[bytes] = None
    error: Optional[str] = None

def generate_speech(text: str, voice_id: str | None = None) -> TTSResult:
    """
    Synthesizes speech from text using ElevenLabs API.
    voice_id defaults to ELEVENLABS_VOICE_ID from settings.
    """
    api_key = settings.ELEVENLABS_API_KEY
    if not voice_id:
        voice_id = settings.ELEVENLABS_VOICE_ID
    if not api_key:
        return TTSResult(error="ELEVENLABS_API_KEY is not configured.")
        
    if not text or not text.strip():
        return TTSResult(error="Text is empty or invalid.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=30.0)
            
        if response.status_code == 200:
            return TTSResult(audio_data=response.content)
        else:
            logger.error(f"TTS API Error {response.status_code}: {response.text}")
            return TTSResult(error=f"TTS API Error: {response.status_code}")
    except Exception as e:
        logger.error(f"TTS execution failed: {e}")
        return TTSResult(error=f"TTS execution failed: {str(e)}")
