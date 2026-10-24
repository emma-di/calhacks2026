import assets from "../../../hardware/oled-assets.json";
import policy from "../../../audio/alert-policy.json";
import { tierNames, type EventType, type SoundEvent } from "../lib/events";
import type { Appearance } from "../lib/appearance";
import { cuePresentation } from "../lib/presentation";

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

export function SoundIcon({ type, size = 24 }: { type: EventType; size?: number }) {
  return (
    <svg
      className="pixel-icon"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      shapeRendering="crispEdges"
      aria-hidden="true"
    >
      <path d={paths[iconIds[type] ?? "bell"]} fill="currentColor" />
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
  const presentation = cuePresentation(event, appearance, direction);
  const visible = presentation && event;
  const text = presentation?.label;
  return (
    <div
      className={`cue-region edge-${visible ? direction : "unknown"}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {visible ? (
        <div
          key={event.event_id}
          className={`cue tier-${event.priority_tier} ${text ? "" : "icon-only"} ${appearance.motion === "gentle" ? "gentle-cue" : ""}`}
          role="group"
          aria-label={`${tierNames[event.priority_tier]}: ${event.label}`}
          style={{
            color: appearance.colors[event.priority_tier],
            borderColor: appearance.colors[event.priority_tier],
          }}
        >
          <span className="cue-symbol">
            <SoundIcon type={event.type} size={32} />
          </span>
          {text && <strong>{event.label}</strong>}
        </div>
      ) : (
        <div className="cue-idle">
          <span className="idle-orbit" />
          <span>Quiet. Play a sound to see its cue here.</span>
        </div>
      )}
    </div>
  );
}
