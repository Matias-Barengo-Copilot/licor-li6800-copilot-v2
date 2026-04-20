"""
LLM service: Gemini chat with RAG context injection.

Text chunks are injected as context text.
Video chunks are loaded from disk, cut to their segment window with ffmpeg,
and passed as inline video bytes so Gemini can watch the relevant clip.

chat()        — synchronous, returns a complete ChatResponse.
stream_chat() — async generator, yields streaming events for the WebSocket.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from google import genai
from google.genai import types

CHAT_MODEL = "gemini-2.5-flash"
MAX_HISTORY_TURNS = 5
MAX_CONTEXT_CHARS = 8000
MAX_VIDEO_CHUNKS = 2

SYSTEM_PROMPT = """You are the LI-COR LI-6800 Expert Assistant — a knowledgeable, professional guide for researchers and scientists who just received their LI-6800 Portable Photosynthesis System.

Your role:
- Answer questions about setup, operation, troubleshooting, and maintenance of the LI-6800
- Reference the provided context (manual excerpts, research papers, and video clips) when answering
- Be precise and technically accurate — your users are plant biologists, ecologists, and agronomists
- Stay on topic: only answer questions related to the LI-6800 and LI-COR Environmental products

Response format:
- For most answers: respond with plain text only
- When your answer includes quantitative data that would be clearer as a chart, respond with JSON in this exact format:
  {"text": "Your explanation here", "graph": {"type": "bar", "title": "Chart title", "labels": ["A", "B"], "values": [1.0, 2.0]}, "citations": [{"source": "manual", "section": "3.2"}]}
- Only include "graph" when the data is explicitly present in the context — never fabricate chart data
- "citations" is optional — include it when you can identify a specific source and section
- If the context does not contain enough information to answer, say so clearly rather than guessing"""


@dataclass
class ChatResponse:
    text: str
    graph: dict | None = field(default=None)
    citations: list[dict] | None = field(default=None)


def _cut_segment(local_file: str, start_time: int, end_time: int) -> bytes | None:
    fs_path = local_file.lstrip("/")
    if not os.path.exists(fs_path):
        return None
    duration = end_time - start_time
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["ffmpeg", "-ss", str(start_time), "-i", fs_path,
             "-t", str(duration), "-c", "copy", "-y", tmp_path],
            capture_output=True,
        )
        if result.returncode != 0:
            return None
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _build_user_parts(
    query: str,
    context_chunks: list[dict],
    image: dict | None = None,
) -> list[types.Part]:
    text_chunks = [c for c in context_chunks if c.get("type") != "video"]
    video_chunks = [c for c in context_chunks if c.get("type") == "video"]

    parts: list[types.Part] = []

    context = ""
    for chunk in text_chunks:
        entry = f"[Source: {chunk['source']}]\n{chunk['text']}\n\n"
        if len(context) + len(entry) > MAX_CONTEXT_CHARS:
            break
        context += entry
    if context:
        parts.append(types.Part.from_text(
            text=f"Context from the LI-6800 documentation:\n{context.strip()}"
        ))

    for chunk in video_chunks[:MAX_VIDEO_CHUNKS]:
        video_bytes = _cut_segment(
            chunk.get("local_file", ""),
            int(chunk.get("start_time", 0)),
            int(chunk.get("end_time", 0)),
        )
        if video_bytes:
            parts.append(types.Part.from_text(
                text=f"[Video clip: {chunk['source']} "
                     f"{chunk.get('start_time', 0)}s–{chunk.get('end_time', 0)}s]"
            ))
            parts.append(types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"))

    if image:
        parts.append(types.Part.from_bytes(
            data=image["data"], mime_type=image["mime_type"]
        ))

    parts.append(types.Part.from_text(text=f"Question: {query}"))
    return parts


def _build_history_contents(history: list[dict]) -> list[types.Content]:
    contents = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=turn["user"])],
        ))
        contents.append(types.Content(
            role="model",
            parts=[types.Part.from_text(text=turn["assistant"])],
        ))
    return contents


def _parse_response(raw: str) -> ChatResponse:
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            return ChatResponse(
                text=data.get("text", stripped),
                graph=data.get("graph"),
                citations=data.get("citations"),
            )
        except json.JSONDecodeError:
            pass
    return ChatResponse(text=stripped)


class LLMService:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    def chat(
        self,
        query: str,
        context_chunks: list[dict],
        conversation_history: list[dict],
        image: dict | None = None,
    ) -> ChatResponse:
        """Synchronous chat — used by the HTTP /chat endpoint."""
        contents = _build_history_contents(conversation_history)
        contents.append(types.Content(
            role="user",
            parts=_build_user_parts(query, context_chunks, image),
        ))

        response = self._client.models.generate_content(
            model=CHAT_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
            ),
        )
        return _parse_response(response.text or "")

    async def stream_chat(
        self,
        query: str,
        context_chunks: list[dict],
        conversation_history: list[dict],
        image: dict | None = None,
    ) -> AsyncIterator[dict]:
        """
        Async generator — used by the WebSocket endpoint.

        Yields dicts:
          {"type": "text",      "text": "..."}
          {"type": "graph",     "graph": {...}}
          {"type": "citations", "citations": [...]}
        """
        contents = _build_history_contents(conversation_history)
        contents.append(types.Content(
            role="user",
            parts=_build_user_parts(query, context_chunks, image),
        ))

        buffer = ""
        is_json: bool | None = None  # None = not yet determined

        async for chunk in await self._client.aio.models.generate_content_stream(
            model=CHAT_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
            ),
        ):
            token = chunk.text
            if not token:
                continue

            buffer += token

            if is_json is None and len(buffer) >= 5:
                is_json = buffer.lstrip().startswith("{")
                if is_json is False:
                    # Flush the buffered prefix — we now know it's plain text
                    yield {"type": "text", "text": buffer}
            elif is_json is False:
                # Already confirmed plain text — stream token by token
                yield {"type": "text", "text": token}
            # is_json True or still None → keep buffering

        # Post-stream flush
        if is_json is True:
            parsed = _parse_response(buffer)
            yield {"type": "text", "text": parsed.text}
            if parsed.graph:
                yield {"type": "graph", "graph": parsed.graph}
            if parsed.citations:
                yield {"type": "citations", "citations": parsed.citations}
        elif is_json is None and buffer:
            # Very short response (< 5 chars) — emit as-is
            yield {"type": "text", "text": buffer}

