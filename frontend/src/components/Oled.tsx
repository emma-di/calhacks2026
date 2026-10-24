import { useEffect, useRef } from "react";
import policy from "../../../audio/alert-policy.json";
import type { SoundEvent } from "../lib/events";
import { HEIGHT, WIDTH, render } from "../lib/oled";

const iconIds = policy.icons as Record<string, string>;

// Draws the exact frame hardware/display.py sends to the SSD1306 (tests compare them byte for byte).
// The monochrome panel uses compass arrows only when direction is supplied.
// `lens` draws the same frame as the wearer sees it through the 50:50 combiner: unlit pixels are
// see-through instead of black.
export default function Oled({
  event,
  labels,
  direction = null,
  lens = false,
}: {
  event: SoundEvent | null;
  labels: boolean;
  direction?: string | null;
  lens?: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const cue =
    event && event.priority_tier > 0 && iconIds[event.type]
      ? { icon_id: iconIds[event.type], label: event.label, effective_tier: event.priority_tier, remaining_ms: 1, direction }
      : null;
  const key = cue ? `${event!.event_id}:${cue.effective_tier}:${labels}:${direction}` : "blank";
  useEffect(() => {
    const ctx = canvas.current?.getContext("2d");
    if (!ctx) return;
    const bitmap = render(cue, labels);
    const image = ctx.createImageData(WIDTH, HEIGHT);
    for (let y = 0; y < HEIGHT; y++)
      for (let x = 0; x < WIDTH; x++) {
        const v = bitmap.get(x, y) ? 255 : 0;
        const i = (y * WIDTH + x) * 4;
        image.data[i] = image.data[i + 1] = image.data[i + 2] = v;
        image.data[i + 3] = lens && !v ? 0 : 255;
      }
    ctx.putImageData(image, 0, 0);
  }, [key, lens]);
  return (
    <canvas
      ref={canvas}
      width={WIDTH}
      height={HEIGHT}
      className={lens ? "lens-bitmap" : "oled-bitmap"}
      role="img"
      aria-label={cue ? `Glasses display: ${event!.label}` : "Glasses display: blank"}
    />
  );
}
