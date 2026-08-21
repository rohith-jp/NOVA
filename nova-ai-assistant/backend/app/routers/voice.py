"""Voice router — STT transcription endpoint."""
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.stt import transcribe_audio

router = APIRouter(prefix="/api/voice", tags=["voice"])


class TranscriptionResponse(BaseModel):
    text: str


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(audio: UploadFile = File(...)) -> TranscriptionResponse:
    """
    Accepts a raw audio file upload and returns Whisper transcription text.

    The audio is sent to OpenAI Whisper and the transcript is returned.
    No audio is persisted on the server.
    """
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type: {audio.content_type!r}. Send an audio/* file.",
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    result = transcribe_audio(audio_bytes, filename=audio.filename or "recording.webm")

    if result.error:
        raise HTTPException(status_code=502, detail=result.error)

    return TranscriptionResponse(text=result.text)
