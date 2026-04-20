/**
 * pcm-recorder-processor.js
 *
 * AudioWorklet processor that runs on the dedicated audio thread.
 * Converts Float32 Web Audio frames → Int16 PCM and posts them to the main thread.
 * The main thread forwards each buffer as a binary WebSocket frame.
 *
 * Required sample rate: 16 000 Hz (set on the AudioContext in app.js).
 */

class PCMRecorderProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;

    // Convert Float32 [-1, 1] → Int16 [-32768, 32767]
    const int16 = new Int16Array(channel.length);
    for (let i = 0; i < channel.length; i++) {
      const clamped = Math.max(-1, Math.min(1, channel[i]));
      int16[i] = clamped < 0 ? clamped * 32768 : clamped * 32767;
    }

    // Transfer ownership to avoid a copy on the main thread
    this.port.postMessage(int16.buffer, [int16.buffer]);
    return true; // keep processor alive
  }
}

registerProcessor('pcm-recorder', PCMRecorderProcessor);
