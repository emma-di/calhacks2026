import assets from "../../../hardware/oled-assets.json";
import policy from "../../../audio/alert-policy.json";
import { type EventType, type SoundEvent } from "../lib/events";
import type { Appearance } from "../lib/appearance";
import Oled from "./Oled";

const bitmaps = assets.bitmaps as Record<string, string[]>;
const iconIds = policy.icons as Record<string, string>;
// Each icon becomes one SVG path of pixel runs, so the site uses the glasses' own pixel art.
const paths: Record<string, string> = Object.fromEntries(
  Object.entries(bitmaps).map(([id, rows]) => [
    id,
    rows
      .flatMap((bits, y) => [...bits.matchAll(/1+/g)].map((m) => `M${m.index} ${y}h${m[0].length}v1h-${m[0].length}z`))
      .join(""),
  ]),
);

export function SoundIcon({ type, iconId, size = 24 }: { type: EventType; iconId?: string; size?: number }) {
  return (
    <svg
      className="pixel-icon"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      shapeRendering="crispEdges"
      aria-hidden="true"
    >
      <path d={paths[iconId ?? iconIds[type] ?? "wave"]} fill="currentColor" />
    </svg>
  );
}
export default function Cue({
  event,
  appearance,
  direction,
}: {
  event: SoundEvent | null;
  appearance: Appearance;
  direction: Appearance["direction"];
}) {
  return (
    <div className={`lens-frame ${event ? "is-lit" : ""} ${appearance.motion === "gentle" ? "gentle-cue" : ""}`}>
      <Oled event={event} labels={appearance.text === "labels"}
        direction={direction === "unknown" ? null : direction} lens />
    </div>
  );
}
