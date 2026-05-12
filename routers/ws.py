"""
WebSocket endpoint — Gemini Live API bidirectional streaming.

Each connection opens a persistent Gemini Live session and runs two
concurrent tasks:

  _upstream   — reads messages from the browser and forwards them to Gemini
  _downstream — reads events from Gemini and forwards them to the browser

Client → Server messages
────────────────────────
{"type": "text", "text": "..."}
    User typed a message.  RAG retrieval + Live API text turn.

{"type": "audio_start"}
    Push-to-talk started.  Begin buffering incoming binary PCM frames.

<binary WebSocket frame>
    Raw 16 kHz Int16 mono PCM chunk produced by the AudioWorklet.

{"type": "audio_end"}
    Push-to-talk released.  Server transcribes buffer via Deepgram,
    runs RAG, and sends as a Live API text turn.

{"type": "video_frame", "data": "<base64-jpeg>", "mimeType": "image/jpeg"}
    One 1-fps JPEG frame from the browser's camera or screen-share.
    Forwarded directly to the Live API as realtime visual context.

Server → Client messages
────────────────────────
<binary WebSocket frame>
    24 kHz Int16 mono PCM audio chunk from Gemini's voice response.

{"outputTranscription": {"text": "..."}}
    Incremental text transcription of what Gemini just said.

{"inputTranscription": {"text": "...", "finished": true}}
    User's voice transcript (from Deepgram PTT).

{"turnComplete": true}
    Gemini has finished the current response turn.

{"interrupted": true}
    Gemini's output was interrupted (e.g. user started speaking).

{"error": "..."}
    Non-fatal error notification.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.live import LiveSession, create_live_session
from services.rag import build_rag_service
from services.voice import VoiceService

router = APIRouter()
logger = logging.getLogger(__name__)

# Services are initialised once at module load and shared across all connections
_rag_service, _ = build_rag_service()
_voice_service = VoiceService()

# 60 s of 16 kHz Int16 mono = 1.92 MB
_MAX_AUDIO_BYTES = 60 * 16_000 * 2


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"[WS] connected: {session_id}", flush=True)
    logger.info("WS connected: %s", session_id)

    try:
        print(f"[WS] opening Live session: {session_id}", flush=True)
        async with create_live_session(_rag_service, _voice_service) as live:
            print(f"[WS] Live session ready: {session_id}", flush=True)
            upstream = asyncio.create_task(_upstream(websocket, live))
            downstream = asyncio.create_task(_downstream(websocket, live))

            done, pending = await asyncio.wait(
                {upstream, downstream},
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel whichever task is still running
            for task in pending:
                task.cancel()
                try:
                    await task
                except (Exception, asyncio.CancelledError):
                    pass

            # Log unexpected errors (WebSocketDisconnect is expected)
            for task in done:
                try:
                    exc = task.exception()
                except asyncio.CancelledError:
                    exc = None
                if exc and not isinstance(exc, (WebSocketDisconnect, asyncio.CancelledError)):
                    logger.warning("WS task error in session %s: %s", session_id, exc)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("WS session error: %s", session_id)
        try:
            await websocket.send_json({"error": f"Session failed: {exc}"})
        except Exception:
            pass
    finally:
        logger.info("WS disconnected: %s", session_id)


# ── Upstream: browser → Live API ───────────────────────────────────────────

async def _upstream(websocket: WebSocket, live: LiveSession) -> None:
    is_recording = False

    while True:
        msg = await websocket.receive()

        # Low-level receive() returns a disconnect message instead of raising.
        if msg.get("type") == "websocket.disconnect":
            raise WebSocketDisconnect(code=msg.get("code", 1000))

        if "bytes" in msg:
            # Binary frame: raw 16 kHz PCM chunk — stream directly to Gemini VAD
            if is_recording:
                await live.send_audio_chunk(bytes(msg["bytes"]))

        elif "text" in msg:
            data = json.loads(msg["text"])
            kind = data.get("type")

            if kind == "text":
                try:
                    await live.send_text(data.get("text", ""))
                except Exception as exc:
                    logger.exception("send_text failed")
                    try:
                        await websocket.send_json({"error": f"Failed to send message: {exc}"})
                    except Exception:
                        pass

            elif kind == "audio_start":
                is_recording = True

            elif kind == "audio_end":
                is_recording = False
                await live.send_audio_stream_end()

            elif kind == "video_frame":
                try:
                    jpeg_bytes = base64.b64decode(data["data"])
                    await live.send_video_frame(jpeg_bytes)
                except Exception as exc:
                    logger.warning("Video frame error: %s", exc)


# ── Downstream: Live API → browser ─────────────────────────────────────────

async def _downstream(websocket: WebSocket, live: LiveSession) -> None:
    async for event in live.events():
        if event.type == "audio":
            await websocket.send_bytes(event.audio)

        elif event.type == "output_transcription":
            await websocket.send_json({"outputTranscription": {"text": event.text}})

        elif event.type == "input_transcription":
            await websocket.send_json({
                "inputTranscription": {"text": event.text, "finished": True}
            })

        elif event.type == "turn_complete":
            await websocket.send_json({"turnComplete": True})

        elif event.type == "interrupted":
            await websocket.send_json({"interrupted": True})

        elif event.type == "error":
            await websocket.send_json({"error": event.text})
