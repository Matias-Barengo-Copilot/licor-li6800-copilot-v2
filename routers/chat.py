"""
HTTP chat endpoints (kept for backward compatibility).
The primary real-time interface is the WebSocket at /ws/{session_id}.

POST /chat        — RAG retrieval + Gemini response
POST /transcribe  — audio → Deepgram transcript
POST /speak       — text → ElevenLabs MP3 stream
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from services.llm import LLMService
from services.rag import build_rag_service
from services.voice import VoiceService

router = APIRouter()

_rag_service, _ = build_rag_service()
_llm_service = LLMService()
_voice_service = VoiceService()


class HistoryTurn(BaseModel):
    user: str
    assistant: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryTurn] = []


class SpeakRequest(BaseModel):
    text: str


@router.post("/chat")
async def chat(request: ChatRequest):
    chunks = _rag_service.retrieve(request.message)
    history = [turn.model_dump() for turn in request.history]
    response = _llm_service.chat(request.message, chunks, history)
    return {
        "text": response.text,
        "graph": response.graph,
        "citations": response.citations,
    }


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")
    transcript = _voice_service.transcribe(
        audio_bytes, mime_type=file.content_type or "audio/webm"
    )
    return {"transcript": transcript}


@router.post("/speak")
async def speak(request: SpeakRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    audio = _voice_service.synthesize(request.text)
    if audio is None:
        return JSONResponse(status_code=204, content=None)
    return Response(content=audio, media_type="audio/mpeg")
