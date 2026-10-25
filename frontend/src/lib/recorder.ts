// Browser recording for teaching: microphone -> live analyser (for the meter) -> 16 kHz mono WAV.
// Echo cancellation, noise suppression and auto gain are off: they treat many alert sounds as noise.

export interface Recording {
  analyser: AnalyserNode;
  startedAt: number;
  maxSeconds: number;
  stop: () => void;
  done: Promise<Blob>; // resolves with a 16 kHz mono 16-bit WAV
}

export async function startRecording(maxSeconds: number): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
  });
  const context = new AudioContext();
  const analyser = context.createAnalyser();
  analyser.fftSize = 1024;
  context.createMediaStreamSource(stream).connect(analyser);
  const recorder = new MediaRecorder(stream);
  const chunks: Blob[] = [];
  recorder.ondataavailable = (e) => chunks.push(e.data);
  const stopped = new Promise<void>((resolve) => (recorder.onstop = () => resolve()));
  const stop = () => {
    if (recorder.state === "recording") recorder.stop();
  };
  const timer = setTimeout(stop, maxSeconds * 1000);
  recorder.start();
  const done = stopped.then(async () => {
    clearTimeout(timer);
    stream.getTracks().forEach((t) => t.stop());
    void context.close();
    return toWav16k(new Blob(chunks, { type: recorder.mimeType }));
  });
  return { analyser, startedAt: performance.now(), maxSeconds, stop, done };
}

/** Decode whatever the browser recorded (WebM/Opus, MP4/AAC), mix to mono, resample to 16 kHz WAV. */
export async function toWav16k(blob: Blob): Promise<Blob> {
  const decoder = new AudioContext();
  const decoded = await decoder.decodeAudioData(await blob.arrayBuffer());
  void decoder.close();
  const frames = Math.max(1, Math.ceil(decoded.duration * 16000));
  const offline = new OfflineAudioContext(1, frames, 16000);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  return encodeWav((await offline.startRendering()).getChannelData(0), 16000);
}

export function encodeWav(samples: Float32Array, rate: number): Blob {
  const view = new DataView(new ArrayBuffer(44 + samples.length * 2));
  const text = (offset: number, s: string) =>
    [...s].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  text(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVEfmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  text(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((x, i) => view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, x)) * 32767, true));
  return new Blob([view], { type: "audio/wav" });
}
