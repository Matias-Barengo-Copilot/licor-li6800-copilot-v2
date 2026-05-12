# LI-6800 Copilot — Engineer Onboarding

This is an AI assistant for the LI-COR LI-6800 Portable Photosynthesis System. It's a FastAPI app with a Gemini Live API voice backend and a vanilla JS frontend. No build step, no framework — just Python and browser JS.

---

## Get it running

```bash
conda activate licor-copilot
uvicorn main:app --reload --port 8000
```

Then open `http://localhost:8000`.

If you're on a fresh machine:

```bash
conda create -n licor-copilot python=3.11 -y
conda activate licor-copilot
pip install -r requirements.txt
```

You'll need a `.env` file with three keys:

```
GOOGLE_API_KEY=...      # Gemini (Live API + embeddings)
DEEPGRAM_API_KEY=...    # Deepgram (legacy STT path — still needed at startup)
OPENAI_API_KEY=...      # Only used by an optional embedding fallback, can be a dummy
```

---

## The one-minute mental model

The page has two things: a landing page (videos, docs) and a floating chat widget. The chat widget opens a WebSocket to the backend, which maintains a live Gemini session for the duration of the connection. The user talks → browser streams PCM audio to Gemini → Gemini responds with PCM audio + text transcription → browser plays it back.

Before sending any query (voice or text), the backend runs a quick RAG lookup against a ChromaDB vector store of LI-6800 documentation and prepends the relevant excerpts to the message. Gemini always answers with the manual in context.

That's the whole thing.

---

## How a request actually works

### Voice query

```
User speaks
    │
    ▼
pcm-recorder-processor.js (AudioWorklet, audio thread)
  Converts Float32 mic frames → Int16 PCM, posts buffer to main thread
    │
    ▼
app.js (main thread)
  Sends each buffer as a raw binary WebSocket frame
    │
    ▼
ws.py — _upstream()
  Receives binary frames, calls live.send_audio_chunk(pcm_bytes)
    │
    ▼
live.py — send_audio_chunk()
  session.send_realtime_input(audio=Blob(data, mime="audio/pcm;rate=16000"))
    │
    ▼
Gemini Live API
  Runs its own VAD (voice activity detection) to detect when the user
  has finished speaking, then generates a response
    │
    ▼
live.py — _receive_loop()
  Reads session.receive() in a loop, puts LiveEvent objects on an async queue:
    - type="audio"                → raw 24 kHz Int16 PCM chunk
    - type="output_transcription" → incremental text of what Gemini is saying
    - type="input_transcription"  → what Gemini heard the user say
    - type="turn_complete"        → Gemini finished speaking
    │
    ▼
ws.py — _downstream()
  Drains the queue and sends to browser:
    - audio events  → binary WebSocket frames
    - everything else → JSON
    │
    ▼
app.js (main thread)
  Binary frames → enqueuePCMAudio() → posts to pcm-player-processor.js
  JSON events   → handleServerEvent() → updates chat transcript
    │
    ▼
pcm-player-processor.js (AudioWorklet, audio thread)
  Maintains a ring buffer, drains it frame-by-frame into the speaker output.
  Outputs silence on underrun. Flushes on { type: 'clear' } (interrupt).
```

RAG is layered in on **text and PTT turns only** — voice streamed natively to Gemini doesn't go through RAG because there's no text to search with until after Gemini transcribes it. For text messages sent via the input box, `live.send_text()` runs the RAG lookup first and prepends the results before calling `send_client_content`.

### Camera / screen share

Camera and screen share work independently of the query cycle. Once the user starts streaming, a `setInterval` fires every second in `app.js`, captures a JPEG frame from an offscreen `<canvas>`, and sends it as:

```json
{ "type": "video_frame", "data": "<base64-jpeg>", "mimeType": "image/jpeg" }
```

`ws.py` decodes the base64 and calls `live.send_video_frame(jpeg_bytes)`, which forwards it via `send_realtime_input(video=...)`. Gemini accumulates these frames as continuous visual context — it can reference what it sees in any response, not just the next one. There's no "send a photo and ask a question" pairing; the frames just flow in the background.

---

## How the AudioWorklets work

The Web Audio API runs audio processing on a dedicated high-priority thread separate from the main JS thread. AudioWorklet processors live on that thread — they can't touch the DOM or make network calls, but they can exchange data with the main thread via `MessagePort`.

**Recording (`pcm-recorder-processor.js`)**

The `process()` method is called by the browser on every audio frame (~128 samples at 16 kHz). It:
1. Takes the Float32 input from the mic (values −1 to +1)
2. Converts to Int16 (multiply by 32767/32768, clamp)
3. Transfers the `ArrayBuffer` to the main thread with zero-copy ownership transfer

The main thread receives it via `recorderNode.port.onmessage` and sends it straight down the WebSocket as a binary frame. No buffering — every worklet callback becomes one WebSocket message.

**Playback (`pcm-player-processor.js`)**

The player maintains a simple append-only ring buffer (`Int16Array`). The main thread posts incoming PCM chunks from Gemini to it as they arrive. The `process()` method drains `frameCount` samples from the front of the buffer on each audio callback, converting Int16 back to Float32 for the speaker. If the buffer runs dry (Gemini is slow or paused), it outputs silence rather than glitching.

When Gemini is interrupted (user starts speaking mid-response), `app.js` sends `{ type: 'clear' }` to the player worklet, which empties the buffer immediately so stale audio doesn't play after the interruption.

**Why two separate AudioContexts?**

Recording needs 16 kHz (what Gemini's audio input expects). Playback needs 24 kHz (what Gemini's audio output produces). A single AudioContext has one fixed sample rate, so they're kept separate — `audioContext` at 16 kHz for the mic, `pcmCtx` at 24 kHz for the speaker.

---

## Voice start / stop in detail

The mic button is a click-to-toggle. Here's what happens at each transition:

**Start (user clicks mic, `isRecording` is false)**

```
startRecording() in app.js
  1. Creates AudioContext at 16 kHz
  2. Loads pcm-recorder-processor.js as an AudioWorklet module
  3. Requests mic via getUserMedia (browser permission prompt if first time)
  4. Creates MediaStreamSource from mic track
  5. Creates AudioWorkletNode('pcm-recorder') and connects source → node
  6. Registers port.onmessage to forward PCM buffers as binary WS frames
  7. Sends {"type": "audio_start"} JSON to server
  8. Sets isRecording = true, lights up the mic button
```

The server receives `audio_start` and sets its own `is_recording = True` flag, which gates whether it forwards binary frames to Gemini. This prevents stray frames from being sent before the user is intentionally recording.

**Stop (user clicks mic again, `isRecording` is true)**

```
stopRecording() in app.js
  1. Sets isRecording = false (stops forwarding buffers from the worklet)
  2. Sends {"type": "audio_end"} JSON to server
  3. Disconnects the worklet node
  4. Stops all mic tracks (releases the mic hardware)
  5. Closes the AudioContext
```

The server receives `audio_end` and calls `live.send_audio_stream_end()`, which sends `send_realtime_input(audio_stream_end=True)` to Gemini. This is the signal Gemini uses to know the user has finished speaking — it finalises VAD and starts generating its response.

Note: with native VAD enabled, Gemini may actually start responding before `audio_stream_end` arrives if it detects a long enough silence. The `audio_stream_end` is a hard stop signal, not the only way a turn ends.

---

## Most likely changes and where to make them

### Change the assistant's tone or personality

`services/live.py` — the `_SYSTEM_PROMPT` string near the top. Rewrite it however you like. The model is `LIVE_MODEL = "gemini-3.1-flash-live-preview"` just above it if that needs to change too.

### Change the voice

Same file, bottom of `create_live_session`:

```python
prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
```

Gemini Live API voices: `Aoede`, `Charon`, `Fenrir`, `Kore`, `Puck`. Swap the name and restart the server.

### Change the videos or add new ones

`services/content.py` — the `VIDEOS` list. Each entry has a `wistia_id` (the ID from the Wistia URL), a title, description, and duration label. Add, remove, or reorder entries here.

The manual and quick-start guide links are `MANUAL` and `QUICK_START` in the same file.

### Front-end tweaks — layout and copy

`templates/index.html` — the entire page lives here (hero text, section headings, chat widget HTML). It's a Jinja2 template but 99% of it is just HTML. The chat widget is the `<div id="chat-panel">` block at the bottom.

`templates/base.html` — the shell: `<head>`, fonts, Tailwind config, and the script tags.

### Front-end tweaks — colors

Colors are defined in the Tailwind config inside `base.html`:

```js
licor: {
  navy:   '#0B1E3D',
  teal:   '#00A0A0',
  teallt: '#00C8C8',
  silver: '#A8B4C0',
  dark:   '#071529',
  card:   '#0F2847',
  border: '#1A3A5C',
}
```

Change a hex value here and it propagates everywhere via Tailwind classes (`bg-licor-teal`, `text-licor-silver`, etc).

### Front-end tweaks — behaviour

`static/js/app.js` — WebSocket client, mic/camera/screen-share logic, audio playback, and the chat message rendering. Well commented.

`static/js/ui.js` — video card click-to-play, chat panel open/close, scroll reveal animations.

`static/css/main.css` — small set of custom styles on top of Tailwind (recording state, citation badges, reveal animation).

---

## Deeper changes (if needed)

### The RAG knowledge base

Documents are in `data/documents/` as plain `.txt` files. The ChromaDB vector store is at `data/chroma/`. If you add a document you need to re-embed it — there's no ingestion script yet, you'd need to call `EmbeddingService.embed()` from `services/rag.py` and add the result to the collection manually (or write a small script).

`services/rag.py` has the retrieval logic — thresholds, candidate count, and the video score multiplier are constants at the top.

### The WebSocket protocol

`routers/ws.py` is the boundary between browser and backend. The full message protocol is documented in the docstring at the top of the file. If you need to add a new message type (e.g. a settings change from the UI), add a new `elif kind == "..."` branch in `_upstream` and handle it in `services/live.py`.

### Adding HTTP endpoints

`routers/chat.py` is the legacy text-only HTTP endpoint — useful as a reference if you need to add a REST endpoint.

---

## File map

```
main.py                          FastAPI app — mounts static files, wires up routers
routers/
  pages.py                       GET / → renders index.html
  chat.py                        POST /chat (legacy text endpoint)
  ws.py                          WebSocket /ws/{session_id}
services/
  live.py                        Gemini Live API session (voice + video + RAG)
  rag.py                         ChromaDB retrieval + Gemini embeddings
  voice.py                       Deepgram STT (legacy path)
  content.py                     Videos, papers, manual links
templates/
  base.html                      Page shell
  index.html                     Full page content + chat widget
static/
  js/app.js                      WebSocket client + audio/video/chat UI
  js/ui.js                       Video cards + chat panel open/close
  js/pcm-recorder-processor.js   AudioWorklet: mic → 16 kHz PCM
  js/pcm-player-processor.js     AudioWorklet: 24 kHz PCM → speaker
  css/main.css                   Custom styles
data/
  documents/                     LI-6800 docs as plain text (RAG source)
  chroma/                        ChromaDB vector store (committed, ready to use)
```
