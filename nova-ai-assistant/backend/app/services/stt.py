import httpx
import logging
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class STTResult(BaseModel):
    text: str
    error: Optional[str] = None

def transcribe_audio(audio_data: bytes, filename: str = "audio.wav") -> STTResult:
    """
    Transcribes audio bytes to text using OpenAI Whisper API.
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return STTResult(text="", error="OPENAI_API_KEY is not configured.")
        
    if not audio_data:
        return STTResult(text="", error="Audio data is empty or invalid.")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    files = {
        "file": (filename, audio_data, "audio/wav"),
        "model": (None, "whisper-1")
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, files=files, timeout=30.0)
            
        if response.status_code == 200:
            data = response.json()
            return STTResult(text=data.get("text", "").strip())
        else:
            logger.error(f"STT API Error {response.status_code}: {response.text}")
            return STTResult(text="", error=f"STT API Error: {response.status_code}")
    except Exception as e:
        logger.error(f"STT execution failed: {e}")
        return STTResult(text="", error=f"STT execution failed: {str(e)}")
