/**
 * app.js — LI-6800 Assistant WebSocket client (Gemini Live API edition)
 *
 * Supports:
 *  - Streaming text display via outputTranscription events
 *  - Push-to-talk voice input (AudioWorklet → 16 kHz PCM → WebSocket binary)
 *  - 24 kHz PCM audio playback from Gemini's voice response
 *  - Continuous 1-fps camera or screen-share streaming
 *  - Plotly graph bubbles (legacy — preserved for HTTP /chat compatibility)
 *  - Citation badges (legacy — preserved for HTTP /chat compatibility)
 *
 * Server event protocol:
 *   <binary frame>                               — 24 kHz Int16 PCM from Gemini
 *   {"outputTranscription": {"text":"..."}}      — Gemini's spoken text (incremental)
 *   {"inputTranscription":  {"text":"...","finished":true}} — user's PTT transcript
 *   {"turnComplete": true}                       — Gemini finished speaking
 *   {"interrupted": true}                        — Gemini was interrupted
 *   {"content": {"parts": [{"text":"..."}]}}     — legacy text token (HTTP endpoint)
 *   {"graph": {...}}                             — legacy Plotly chart
 *   {"citations": [...]}                         — legacy citation badges
 *   {"error": "..."}                             — non-fatal error
 */

// ── WebSocket ──────────────────────────────────────────────────────────────

const SESSION_ID = 'session-' + Math.random().toString(36).substring(2, 9);
let ws = null;
let wsReady = false;

function connectWebSocket() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${proto}//${location.host}/ws/${SESSION_ID}`;
  console.log('[LI-6800] Connecting WebSocket →', url);
  ws = new WebSocket(url);
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => {
    console.log('[LI-6800] WebSocket open');
    wsReady = true;
    setStatus('connected');
  };

  ws.onclose = (evt) => {
    console.log('[LI-6800] WebSocket closed', evt.code, evt.reason);
    wsReady = false;
    setStatus('disconnected');
    setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = (err) => {
    console.error('[LI-6800] WebSocket error', err);
    wsReady = false;
    setStatus('disconnected');
  };

  ws.onmessage = (evt) => {
    if (evt.data instanceof ArrayBuffer) {
      // Binary frame = 24 kHz Int16 PCM audio chunk from Gemini
      enqueuePCMAudio(evt.data);
      return;
    }
    handleServerEvent(evt);
  };
}

function setStatus(state) {
  const dot  = document.getElementById('ws-status-dot');
  const text = document.getElementById('ws-status-text');
  if (!dot || !text) return;
  if (state === 'connected') {
    dot.className  = 'w-2 h-2 rounded-full bg-licor-teal animate-pulse';
    text.textContent = 'Connected';
  } else {
    dot.className  = 'w-2 h-2 rounded-full bg-licor-silver';
    text.textContent = 'Reconnecting…';
  }
}

// ── Server event handler ───────────────────────────────────────────────────

let _currentBubble  = null;  // currently-streaming assistant text element
let _currentWrapper = null;  // its outer wrapper div

function handleServerEvent(evt) {
  let data;
  try { data = JSON.parse(evt.data); } catch { return; }

  // Gemini's spoken text — stream incrementally into the assistant bubble
  if (data.outputTranscription?.text != null) {
    appendAssistantToken(data.outputTranscription.text);
    return;
  }

  // Gemini interrupted — stop audio and close the current bubble
  if (data.interrupted) {
    clearPCMAudio();
    _currentBubble  = null;
    _currentWrapper = null;
    return;
  }

  // Turn complete — seal the current bubble
  if (data.turnComplete) {
    _currentBubble  = null;
    _currentWrapper = null;
    scrollToBottom();
    return;
  }

  // User's PTT transcript → show as a user message
  if (data.inputTranscription?.finished) {
    appendMessage('user', data.inputTranscription.text);
    return;
  }

  // ── Legacy HTTP /chat events (kept for backward compatibility) ───────────

  // Streaming text token from the HTTP endpoint
  if (data.content?.parts) {
    for (const part of data.content.parts) {
      if (part.text) appendAssistantToken(part.text);
    }
    return;
  }

  if (data.graph)     { renderGraphBubble(data.graph); return; }
  if (data.citations) { renderCitations(data.citations); return; }

  // Error
  if (data.error) {
    appendMessage('assistant', `⚠ ${data.error}`);
    _currentBubble  = null;
    _currentWrapper = null;
  }
}

// ── Chat UI helpers ────────────────────────────────────────────────────────

const chatMessages = document.getElementById('chat-messages');

function scrollToBottom() {
  if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendMessage(role, text) {
  const isUser = role === 'user';
  const wrapper = document.createElement('div');
  wrapper.className = `flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`;

  if (!isUser) {
    wrapper.appendChild(_makeAvatar());
  }

  const bubble = document.createElement('div');
  bubble.className = isUser
    ? 'bg-licor-teal rounded-2xl rounded-tr-sm px-4 py-3 max-w-xs'
    : 'bg-licor-navy rounded-2xl rounded-tl-sm px-4 py-3 max-w-xs w-full';

  const textEl = document.createElement('p');
  textEl.className = 'text-sm text-white leading-relaxed whitespace-pre-wrap';
  textEl.textContent = text;
  bubble.appendChild(textEl);

  wrapper.appendChild(bubble);
  chatMessages.appendChild(wrapper);
  scrollToBottom();
}

function appendAssistantToken(token) {
  if (!_currentWrapper) {
    _currentWrapper = document.createElement('div');
    _currentWrapper.className = 'flex gap-3';
    _currentWrapper.appendChild(_makeAvatar());

    const bubble = document.createElement('div');
    bubble.className = 'bg-licor-navy rounded-2xl rounded-tl-sm px-4 py-3 max-w-xs w-full';

    _currentBubble = document.createElement('p');
    _currentBubble.className = 'text-sm text-white leading-relaxed whitespace-pre-wrap';
    bubble.appendChild(_currentBubble);

    _currentWrapper.appendChild(bubble);
    chatMessages.appendChild(_currentWrapper);
  }

  _currentBubble.textContent += token;
  scrollToBottom();
}

function _makeAvatar() {
  const av = document.createElement('div');
  av.className = 'w-7 h-7 rounded-full bg-licor-teal/20 border border-licor-teal/30 flex-shrink-0 flex items-center justify-center mt-0.5';
  av.innerHTML = '<div class="w-1.5 h-1.5 rounded-full bg-licor-teal"></div>';
  return av;
}

// ── Graph and citations (legacy) ───────────────────────────────────────────

function renderGraphBubble(graph) {
  const wrapper = _currentWrapper || (() => {
    const w = document.createElement('div');
    w.className = 'flex gap-3';
    w.appendChild(_makeAvatar());
    const bubble = document.createElement('div');
    bubble.className = 'bg-licor-navy rounded-2xl rounded-tl-sm px-4 py-3 flex-1';
    w.appendChild(bubble);
    chatMessages.appendChild(w);
    _currentWrapper = w;
    return w;
  })();

  const bubble = wrapper.querySelector('div:last-child');
  bubble.classList.remove('max-w-xs');
  bubble.classList.add('flex-1');

  const graphDiv = document.createElement('div');
  graphDiv.id = `graph-${Date.now()}`;
  graphDiv.className = 'graph-bubble mt-2';
  bubble.appendChild(graphDiv);

  requestAnimationFrame(() => renderPlotly(graphDiv.id, graph));
  scrollToBottom();
}

function renderPlotly(containerId, graph) {
  const el = document.getElementById(containerId);
  if (!el || typeof Plotly === 'undefined') return;

  const layout = {
    title:        { text: graph.title || '', font: { color: '#A8B4C0', size: 13 } },
    paper_bgcolor:'#071529',
    plot_bgcolor: '#071529',
    font:         { color: '#A8B4C0', size: 11 },
    margin:       { t: 32, r: 12, b: 40, l: 40 },
    xaxis:        { color: '#1A3A5C', gridcolor: '#1A3A5C' },
    yaxis:        { color: '#1A3A5C', gridcolor: '#1A3A5C' },
  };

  let traces;
  if (graph.type === 'bar') {
    traces = [{ type: 'bar', x: graph.labels, y: graph.values, marker: { color: '#00A0A0' } }];
  } else if (graph.type === 'line') {
    traces = [{ type: 'scatter', mode: 'lines+markers', x: graph.labels, y: graph.values, line: { color: '#00A0A0' } }];
  } else if (graph.type === 'scatter') {
    traces = [{ type: 'scatter', mode: 'markers', x: graph.labels, y: graph.values, marker: { color: '#00A0A0' } }];
  } else {
    traces = [{ type: graph.type || 'bar', x: graph.labels, y: graph.values, marker: { color: '#00A0A0' } }];
  }

  Plotly.newPlot(containerId, traces, layout, { displayModeBar: false, responsive: true });
}

function renderCitations(citations) {
  if (!_currentWrapper) return;
  const bubble = _currentWrapper.querySelector('div:last-child');
  const row = document.createElement('div');
  row.className = 'flex flex-wrap gap-1.5 mt-2';
  citations.forEach((c) => {
    const badge = document.createElement('span');
    badge.className = 'citation-badge';
    badge.textContent = c.section ? `${c.source} §${c.section}` : c.source;
    row.appendChild(badge);
  });
  bubble.appendChild(row);
}

// ── Sending text messages ──────────────────────────────────────────────────

const chatInput = document.getElementById('chat-input');
const sendBtn   = document.getElementById('send-btn');

function sendTextMessage() {
  const text = chatInput?.value.trim();
  if (!text) return;
  if (!wsReady) {
    appendMessage('assistant', 'Not connected yet — please wait a moment.');
    return;
  }
  appendMessage('user', text);
  chatInput.value = '';
  autoResize(chatInput);
  ws.send(JSON.stringify({ type: 'text', text }));
}

sendBtn?.addEventListener('click', sendTextMessage);
chatInput?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTextMessage(); }
});
chatInput?.addEventListener('input', () => autoResize(chatInput));

// ── Push-to-talk voice input ───────────────────────────────────────────────

const micBtn      = document.getElementById('mic-btn');
const voiceStatus = document.getElementById('voice-status');

let audioContext = null;
let micStream    = null;
let recorderNode = null;
let isRecording  = false;

async function startRecording() {
  if (isRecording || !wsReady) return;
  try {
    audioContext = new AudioContext({ sampleRate: 16_000 });
    await audioContext.audioWorklet.addModule(
      new URL('/static/js/pcm-recorder-processor.js', location.href).href
    );
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, sampleRate: 16_000, echoCancellation: true },
    });
    const source = audioContext.createMediaStreamSource(micStream);
    recorderNode = new AudioWorkletNode(audioContext, 'pcm-recorder');
    recorderNode.port.onmessage = (evt) => {
      if (isRecording && wsReady) ws.send(evt.data);
    };
    source.connect(recorderNode);

    ws.send(JSON.stringify({ type: 'audio_start' }));
    isRecording = true;
    micBtn?.classList.add('recording');
    voiceStatus?.classList.remove('hidden');
  } catch (err) {
    console.error('Mic error:', err);
    stopRecording();
    if (err.name === 'NotAllowedError') {
      alert('Microphone access was denied. Please allow microphone access and try again.');
    }
  }
}

async function stopRecording() {
  if (!isRecording) return;
  isRecording = false;
  if (wsReady) ws.send(JSON.stringify({ type: 'audio_end' }));
  recorderNode?.disconnect();
  recorderNode = null;
  micStream?.getTracks().forEach((t) => t.stop());
  micStream = null;
  await audioContext?.close();
  audioContext = null;
  micBtn?.classList.remove('recording');
  voiceStatus?.classList.add('hidden');
}

micBtn?.addEventListener('mousedown',  (e) => { e.preventDefault(); startRecording(); });
micBtn?.addEventListener('mouseup',    stopRecording);
micBtn?.addEventListener('mouseleave', stopRecording);
micBtn?.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); }, { passive: false });
micBtn?.addEventListener('touchend',   (e) => { e.preventDefault(); stopRecording(); },  { passive: false });

// ── 24 kHz PCM audio playback (Gemini voice) ──────────────────────────────

let pcmCtx          = null;
let pcmPlayerNode   = null;
let _pcmInitPromise = null;  // guards against concurrent init calls

function _initPCMPlayer() {
  if (_pcmInitPromise) return _pcmInitPromise;
  _pcmInitPromise = (async () => {
    pcmCtx = new AudioContext({ sampleRate: 24_000 });
    if (pcmCtx.state === 'suspended') await pcmCtx.resume();
    await pcmCtx.audioWorklet.addModule(
      new URL('/static/js/pcm-player-processor.js', location.href).href
    );
    pcmPlayerNode = new AudioWorkletNode(pcmCtx, 'pcm-player');
    pcmPlayerNode.connect(pcmCtx.destination);
  })();
  return _pcmInitPromise;
}

function enqueuePCMAudio(arrayBuffer) {
  _initPCMPlayer().then(() => {
    // Transfer the buffer to avoid copying
    pcmPlayerNode.port.postMessage(arrayBuffer, [arrayBuffer]);
  }).catch((err) => console.warn('PCM player init failed:', err));
}

function clearPCMAudio() {
  if (pcmPlayerNode) pcmPlayerNode.port.postMessage({ type: 'clear' });
}

// ── Video streaming (camera or screen share) ───────────────────────────────

let videoStream        = null;   // active MediaStream
let videoEl            = null;   // invisible <video> bound to the stream
let videoCanvas        = null;   // offscreen <canvas> for frame capture
let videoFrameInterval = null;   // setInterval handle for 1-fps loop
let videoSourceType    = null;   // 'camera' | 'screenshare'

const cameraBtn      = document.getElementById('camera-btn');
const screenshareBtn = document.getElementById('screenshare-btn');
const videoStatus    = document.getElementById('video-status');
const videoStatusText = document.getElementById('video-status-text');
const videoStopBtn   = document.getElementById('video-stop-btn');

async function startVideoStreaming(type) {
  if (videoStream) stopVideoStreaming(); // switch source if already active

  try {
    if (type === 'camera') {
      videoStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 360 }, facingMode: 'environment' },
      });
    } else {
      videoStream = await navigator.mediaDevices.getDisplayMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { max: 5 } },
      });
      // Stop streaming if user closes the browser's share dialog
      videoStream.getVideoTracks()[0].addEventListener('ended', stopVideoStreaming);
    }
  } catch (err) {
    console.error('Video stream error:', err);
    if (err.name === 'NotAllowedError') {
      alert(`${type === 'camera' ? 'Camera' : 'Screen share'} access was denied.`);
    }
    return;
  }

  videoSourceType = type;
  videoEl = document.createElement('video');
  videoEl.srcObject = videoStream;
  videoEl.muted = true;
  videoEl.playsInline = true;
  await videoEl.play();

  videoCanvas = document.createElement('canvas');
  videoCanvas.width  = 640;
  videoCanvas.height = 360;

  // 1-fps capture loop
  videoFrameInterval = setInterval(() => {
    if (!wsReady || !videoStream || videoEl.readyState < 2) return;
    videoCanvas.getContext('2d').drawImage(videoEl, 0, 0, 640, 360);
    const base64 = videoCanvas.toDataURL('image/jpeg', 0.7).split(',')[1];
    ws.send(JSON.stringify({ type: 'video_frame', data: base64, mimeType: 'image/jpeg' }));
  }, 1000);

  _setVideoActive(true, type);
}

function stopVideoStreaming() {
  clearInterval(videoFrameInterval);
  videoFrameInterval = null;
  videoStream?.getTracks().forEach((t) => t.stop());
  videoStream   = null;
  videoEl       = null;
  videoCanvas   = null;
  videoSourceType = null;
  _setVideoActive(false, null);
}

function _setVideoActive(active, type) {
  cameraBtn?.classList.toggle('active', active && type === 'camera');
  screenshareBtn?.classList.toggle('active', active && type === 'screenshare');

  if (videoStatus) videoStatus.classList.toggle('hidden', !active);
  if (videoStatusText && active) {
    videoStatusText.textContent = type === 'camera' ? 'Camera streaming…' : 'Screen sharing…';
  }
}

cameraBtn?.addEventListener('click', () => {
  if (videoSourceType === 'camera') {
    stopVideoStreaming();
  } else {
    startVideoStreaming('camera');
  }
});

screenshareBtn?.addEventListener('click', () => {
  if (videoSourceType === 'screenshare') {
    stopVideoStreaming();
  } else {
    startVideoStreaming('screenshare');
  }
});

videoStopBtn?.addEventListener('click', stopVideoStreaming);

// ── Utility ────────────────────────────────────────────────────────────────

window.autoResize = function (el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
};

// ── Init ───────────────────────────────────────────────────────────────────

console.log('[LI-6800] app.js loaded, starting WebSocket');
connectWebSocket();
