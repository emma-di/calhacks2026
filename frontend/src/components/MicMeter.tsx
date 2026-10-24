import { useEffect, useRef, useState } from "react";

const BARS = 64;

/** Live microphone meter shown while recording: a scrolling level history plus elapsed time. */
export default function MicMeter({
  analyser,
  startedAt,
  maxSeconds,
  label,
}: {
  analyser: AnalyserNode;
  startedAt: number;
  maxSeconds: number;
  label: string;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [elapsed, setElapsed] = useState(0);
  const [tooQuiet, setTooQuiet] = useState(false);
  useEffect(() => {
    const samples = new Float32Array(analyser.fftSize);
    const history: number[] = Array(BARS).fill(0);
    let peakSeen = 0;
    let frame = 0;
    let last = 0;
    const draw = (now: number) => {
      frame = requestAnimationFrame(draw);
      if (now - last < 50) return; // ~20 bars per second
      last = now;
      analyser.getFloatTimeDomainData(samples);
      let sum = 0;
      for (const x of samples) sum += x * x;
      const rms = Math.sqrt(sum / samples.length);
      // dB-ish scale so quiet sounds are still visible: -60 dBFS empty, 0 dBFS full.
      const level = Math.min(1, Math.max(0, (20 * Math.log10(rms + 1e-9) + 60) / 60));
      peakSeen = Math.max(peakSeen, level);
      history.push(level);
      history.shift();
      const seconds = (now - startedAt) / 1000;
      setElapsed(seconds);
      setTooQuiet(seconds > 1.5 && peakSeen < 0.35);
      const c = canvas.current;
      const g = c?.getContext("2d");
      if (!c || !g) return;
      const { width, height } = c;
      g.clearRect(0, 0, width, height);
      const step = width / BARS;
      history.forEach((v, i) => {
        const h = Math.max(2, v * height);
        g.fillStyle = v > 0.97 ? "#ffb547" : i === BARS - 1 ? "#f4f2ea" : "rgba(244,242,234,0.65)";
        g.fillRect(i * step + 1, (height - h) / 2, Math.max(1, step - 2), h);
      });
    };
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, [analyser, startedAt]);

  return (
    <div className="mic-meter" role="status" aria-live="polite">
      <span className="rec-dot" aria-hidden="true" />
      <span className="mic-meter-label">{label}</span>
      <canvas ref={canvas} width={320} height={36} aria-hidden="true" />
      <span className="mic-meter-time">
        {elapsed.toFixed(1)} / {maxSeconds} s
      </span>
      {tooQuiet && <span className="mic-meter-hint">Very quiet: move closer to the microphone</span>}
    </div>
  );
}
