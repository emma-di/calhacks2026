import { useEffect, useRef } from "react";
import { tierNames, type SoundEvent } from "../lib/events";

// Exact device dimensions. Threshold the raster to a one-bit image; no antialiasing or gray pixels.
export default function Oled({ event }: { event: SoundEvent | null }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const ctx = ref.current?.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, 128, 64);
    ctx.fillStyle = "#fff";
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 1;
    if (event && event.priority_tier > 0) {
      if (event.priority_tier >= 3) ctx.strokeRect(0.5, 0.5, 127, 63);
      if (event.priority_tier === 4) ctx.strokeRect(2.5, 2.5, 123, 59);
      const glyph =
        event.type === "smoke_alarm"
          ? "!"
          : event.type === "name_called"
            ? "@"
            : event.type === "dog_bark"
              ? "~"
              : event.type === "knock"
                ? "+"
                : "*";
      ctx.font =
        event.priority_tier === 1 ? "12px monospace" : "bold 19px monospace";
      ctx.textAlign = "center";
      ctx.fillText(glyph, 64, 23);
      ctx.font = "10px monospace";
      const words = event.label.toUpperCase().split(" ");
      const lines: string[] = [];
      let line = "";
      for (const word of words) {
        if (ctx.measureText(`${line} ${word}`.trim()).width > 116 && line) {
          lines.push(line);
          line = word;
        } else line = `${line} ${word}`.trim();
      }
      if (line) lines.push(line);
      lines
        .slice(0, 2)
        .forEach((text, i) => ctx.fillText(text.slice(0, 19), 64, 39 + i * 12));
      ctx.font = "6px monospace";
      ctx.fillText(tierNames[event.priority_tier].toUpperCase(), 64, 59);
    } else {
      ctx.strokeRect(60.5, 17.5, 7, 7);
      ctx.font = "8px monospace";
      ctx.textAlign = "center";
      ctx.fillText("NO ACTIVE CUE", 64, 42);
    }
    const bitmap = ctx.getImageData(0, 0, 128, 64);
    for (let i = 0; i < bitmap.data.length; i += 4) {
      const value = bitmap.data[i] >= 128 ? 255 : 0;
      bitmap.data[i] = value;
      bitmap.data[i + 1] = value;
      bitmap.data[i + 2] = value;
      bitmap.data[i + 3] = 255;
    }
    ctx.putImageData(bitmap, 0, 0);
  }, [event]);
  return (
    <canvas
      ref={ref}
      width={128}
      height={64}
      className="oled-bitmap"
      role="img"
      aria-label={`128 by 64 monochrome design preview: ${event?.priority_tier ? event.label : "no active cue"}`}
    />
  );
}
