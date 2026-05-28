import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import get_current_user

voice_router = APIRouter(prefix="/voice", tags=["voice"])


@voice_router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    if file.content_type and not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Only audio uploads are supported")
    audio = await file.read()
    if len(audio) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio must be 10MB or smaller")
    if not os.getenv("OPENAI_API_KEY"):
        return {"text": "", "mode": "mock", "message": "Voice transcription disabled until OPENAI_API_KEY is configured."}
    try:
        from openai import OpenAI
        client = OpenAI()
        result = client.audio.transcriptions.create(
            model=os.getenv("OPENAI_STT_MODEL", "whisper-1"),
            file=(file.filename or "audio.webm", audio, file.content_type or "audio/webm"),
        )
        return {"text": result.text, "mode": "real"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}")
