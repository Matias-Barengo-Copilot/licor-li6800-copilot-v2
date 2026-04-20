/**
 * pcm-player-processor.js — AudioWorklet for 24 kHz Int16 PCM playback.
 *
 * The main thread sends Int16 ArrayBuffers via port.postMessage().
 * On each audio callback the processor drains as many samples as the
 * output buffer needs, outputting silence when the ring buffer runs dry.
 *
 * Special control messages (plain objects):
 *   { type: 'clear' } — flush the ring buffer (use on 'interrupted' events)
 */
class PCMPlayerProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = new Int16Array(0);

    this.port.onmessage = (evt) => {
      if (evt.data?.type === 'clear') {
        this._buffer = new Int16Array(0);
        return;
      }
      // Incoming: transferable ArrayBuffer of Int16 PCM samples
      const incoming = new Int16Array(evt.data);
      const merged = new Int16Array(this._buffer.length + incoming.length);
      merged.set(this._buffer);
      merged.set(incoming, this._buffer.length);
      this._buffer = merged;
    };
  }

  process(_inputs, outputs) {
    const channel = outputs[0]?.[0];
    if (!channel) return true;

    const frameCount = channel.length;

    if (this._buffer.length >= frameCount) {
      // Normal path: drain frameCount samples, convert Int16 → Float32
      for (let i = 0; i < frameCount; i++) {
        channel[i] = this._buffer[i] / 32768;
      }
      this._buffer = this._buffer.slice(frameCount);
    } else {
      // Underrun: drain what we have, fill the rest with silence
      for (let i = 0; i < this._buffer.length; i++) {
        channel[i] = this._buffer[i] / 32768;
      }
      for (let i = this._buffer.length; i < frameCount; i++) {
        channel[i] = 0;
      }
      this._buffer = new Int16Array(0);
    }

    return true; // keep processor alive
  }
}

registerProcessor('pcm-player', PCMPlayerProcessor);
