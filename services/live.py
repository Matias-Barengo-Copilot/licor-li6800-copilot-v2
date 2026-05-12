"""
Gemini Live API session wrapper.

Maintains a persistent bidirectional session with Gemini Live API.

  - RAG context is injected as text on every text/audio query.
  - PTT audio is transcribed via Deepgram first, then sent as
    context-augmented text via send_client_content.
  - Video frames (camera or screen share) are streamed continuously
    at 1 fps via send_realtime_input — no per-query attachment needed.
  - Gemini responds with 24 kHz Int16 PCM audio chunks and incremental
    text transcription of its own speech.

Usage:
    async with create_live_session(rag, voice) as live:
        await asyncio.gather(
            upstream_task(websocket, live),
            downstream_task(websocket, live),
        )
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from services.rag import RAGService
from services.voice import VoiceService

LIVE_MODEL = "gemini-3.1-flash-live-preview"
MAX_CONTEXT_CHARS = 8_000

# Plain-text system prompt — no JSON graph instruction (audio mode speaks responses)
_SYSTEM_PROMPT = """You are the LI-COR LI-6800 Expert Assistant — a knowledgeable, professional guide for researchers and scientists who just received their LI-6800 Portable Photosynthesis System.

Your role:
- Answer questions about setup, operation, troubleshooting, and maintenance of the LI-6800
- Reference the provided context (manual excerpts and research papers) when answering
- Be precise and technically accurate — your users are plant biologists, ecologists, and agronomists
- Stay on topic: only answer questions related to the LI-6800 and LI-COR Environmental products
- When the user shares their camera or screen, only describe or reference what you can clearly and confidently see. Do not speculate or invent details about what might be shown. If the feed is unclear, dark, or ambiguous, say so and ask the user to describe or reposition what they want you to see.

Respond naturally in conversational speech. Be concise and technically precise."""

logger = logging.getLogger(__name__)


@dataclass
class LiveEvent:
    """A single event forwarded from the Gemini Live session to the WS client."""

    type: str
    """
    "audio"               — PCM chunk from Gemini (bytes in .audio)
    "output_transcription"— incremental text transcription of Gemini's speech
    "input_transcription" — user's PTT transcript (from Deepgram, not Gemini)
    "turn_complete"       — Gemini finished the current response turn
    "interrupted"         — Gemini's output was interrupted
    "error"               — non-fatal error message (text in .text)
    """
    text: str = ""
    audio: bytes = field(default_factory=bytes)


class LiveSession:
    """Wraps a google-genai Live API session with RAG and PTT voice support."""

    def __init__(self, session, rag: RAGService, voice: VoiceService) -> None:
        self._session = session
        self._rag = rag
        self._voice = voice
        self._queue: asyncio.Queue[LiveEvent | None] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._task = asyncio.create_task(self._receive_loop())

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Unblock any consumer that is waiting on events()
        await self._queue.put(None)

    # ── Client → Gemini ────────────────────────────────────────────────────

    async def send_text(self, query: str) -> None:
        """RAG-augment the query and send it as a client content turn."""
        chunks = self._rag.retrieve(query)
        context = _build_context(chunks)
        full_text = f"{context}Question: {query}" if context else query
        await self._session.send_client_content(
            turns=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=full_text)],
                )
            ],
            turn_complete=True,
        )

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Stream one raw PCM chunk to Gemini for native VAD processing."""
        await self._session.send_realtime_input(
            audio=types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000"),
        )

    async def send_audio_stream_end(self) -> None:
        """Signal that the audio stream has ended (user stopped mic)."""
        await self._session.send_realtime_input(audio_stream_end=True)

    async def send_video_frame(self, jpeg_bytes: bytes) -> None:
        """Send one JPEG frame as realtime visual context (1 fps stream)."""
        await self._session.send_realtime_input(
            video=types.Blob(data=jpeg_bytes, mime_type="image/jpeg"),
        )

    # ── Gemini → client ────────────────────────────────────────────────────

    async def events(self):  # AsyncGenerator[LiveEvent, None]
        """Async-generator of LiveEvents; terminates when the session ends."""
        while True:
            event = await self._queue.get()
            if event is None:
                return
            yield event

    # ── Internal receive loop ──────────────────────────────────────────────

    async def _receive_loop(self) -> None:
        try:
            # session.receive() is a per-turn iterator — restart it after each
            # turn_complete so the session stays alive across multiple exchanges.
            while True:
                async for response in self._session.receive():
                    sc = getattr(response, "server_content", None)
                    if sc is None:
                        continue  # e.g. setup_complete message

                    # Audio chunks (and optionally text if TEXT modality also enabled)
                    if sc.model_turn:
                        for part in sc.model_turn.parts or []:
                            if getattr(part, "thought", False):
                                continue  # skip internal reasoning tokens
                            inline = getattr(part, "inline_data", None)
                            if inline and inline.data:
                                await self._queue.put(LiveEvent(type="audio", audio=inline.data))
                            elif getattr(part, "text", None):
                                # TEXT modality token (if response_modalities includes TEXT)
                                await self._queue.put(LiveEvent(type="output_transcription", text=part.text))

                    # Transcription of the user's spoken input (native VAD)
                    it = getattr(sc, "input_transcription", None)
                    if it:
                        t = getattr(it, "text", "") or ""
                        if t:
                            await self._queue.put(LiveEvent(type="input_transcription", text=t))

                    # Transcription of Gemini's audio output
                    ot = getattr(sc, "output_transcription", None)
                    if ot:
                        t = getattr(ot, "text", "") or ""
                        if t:
                            await self._queue.put(LiveEvent(type="output_transcription", text=t))

                    if getattr(sc, "interrupted", False):
                        await self._queue.put(LiveEvent(type="interrupted"))

                    if getattr(sc, "turn_complete", False):
                        await self._queue.put(LiveEvent(type="turn_complete"))
                # turn complete — loop back and wait for the next turn

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Live API receive loop error")
        finally:
            await self._queue.put(None)


# ── Context builder ────────────────────────────────────────────────────────

def _build_context(chunks: list[dict]) -> str:
    """Build a plain-text context string from RAG results (skips video chunks)."""
    parts: list[str] = []
    total = 0
    for chunk in chunks:
        if chunk.get("type") == "video":
            continue  # video context arrives via continuous send_video_frame
        entry = f"[Source: {chunk['source']}]\n{chunk['text']}\n\n"
        if total + len(entry) > MAX_CONTEXT_CHARS:
            break
        parts.append(entry)
        total += len(entry)
    if not parts:
        return ""
    return f"Context from the LI-6800 documentation:\n{''.join(parts).strip()}\n\n"


# ── Factory ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def create_live_session(
    rag: RAGService,
    voice: VoiceService,
) -> AsyncIterator[LiveSession]:
    """Async context manager that opens a Gemini Live session and tears it down cleanly."""
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=_SYSTEM_PROMPT,
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
    )
    print(f"[Live] connecting to model: {LIVE_MODEL}", flush=True)
    async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
        print("[Live] model connected", flush=True)
        live = LiveSession(session, rag, voice)
        await live.start()
        try:
            yield live
        finally:
            await live.stop()
