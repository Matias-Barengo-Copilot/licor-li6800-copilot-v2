"""
Voice service: Deepgram Nova-2 STT + ElevenLabs TTS.

transcribe() accepts:
  - audio/webm  — from the legacy MediaRecorder-based mic button
  - audio/pcm   — raw 16 kHz Int16 mono PCM from the AudioWorklet push-to-talk;
                  automatically wrapped in a WAV header before sending to Deepgram

synthesize() returns None if ElevenLabs is unavailable — the frontend falls back
to browser SpeechSynthesis in that case.
"""

from __future__ import annotations

import io
import logging
import os
import struct

from deepgram import DeepgramClient, PrerecordedOptions, BufferSource

logger = logging.getLogger(__name__)

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16_000) -> bytes:
    """Wrap raw Int16 mono PCM bytes in a minimal WAV container."""
    num_channels = 1
    sample_width = 2  # 16-bit = 2 bytes
    data_len = len(pcm_bytes)

    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_len))     # file size - 8
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))                # fmt chunk size
    buf.write(struct.pack("<H", 1))                 # PCM = 1
    buf.write(struct.pack("<H", num_channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * num_channels * sample_width))
    buf.write(struct.pack("<H", num_channels * sample_width))
    buf.write(struct.pack("<H", sample_width * 8))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_len))
    buf.write(pcm_bytes)
    return buf.getvalue()


class VoiceService:
    def __init__(self) -> None:
        self._deepgram = DeepgramClient(api_key=os.environ["DEEPGRAM_API_KEY"])
        self._elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self._voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "") or DEFAULT_VOICE_ID

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        """
        Send audio to Deepgram Nova-2 and return the transcript.

        audio/pcm input is automatically wrapped in a WAV header at 16 kHz
        before submission — this is the format produced by the frontend
        AudioWorklet push-to-talk.
        """
        if mime_type == "audio/pcm":
            audio_bytes = _pcm_to_wav(audio_bytes)
            mime_type = "audio/wav"

        payload: BufferSource = {"buffer": audio_bytes}
        options = PrerecordedOptions(
            model="nova-2-general",
            smart_format=True,
            punctuate=True,
        )
        response = self._deepgram.listen.rest.v("1").transcribe_file(payload, options)
        return response.results.channels[0].alternatives[0].transcript

    def synthesize(self, text: str) -> bytes | None:
        """
        Convert text to speech via ElevenLabs.
        Returns MP3 bytes on success, None if unavailable or the call fails.
        """
        if not self._elevenlabs_key:
            logger.warning("ELEVENLABS_API_KEY not set — skipping TTS")
            return None

        try:
            import httpx

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}"
            headers = {
                "xi-api-key": self._elevenlabs_key,
                "Content-Type": "application/json",
            }
            body = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            }
            resp = httpx.post(url, headers=headers, json=body, timeout=15)
            resp.raise_for_status()
            return resp.content

        except Exception as exc:
            logger.warning(
                "ElevenLabs TTS failed (%s) — frontend will use browser TTS", exc
            )
            return None
