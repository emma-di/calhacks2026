import type { Appearance } from "./appearance";
import type { SoundEvent } from "./events";
// Semantic cue content. Direction describes the arrow, never icon placement.
export function cuePresentation(
  event: SoundEvent | null,
  appearance: Appearance,
  direction: Appearance["direction"],
) {
  if (!event || event.priority_tier === 0) return null;
  return {
    eventId: event.event_id,
    icon: event.type,
    tier: event.priority_tier,
    label:
      appearance.text === "labels" || event.priority_tier === 4
        ? event.label
        : null,
    description: event.label,
    color: appearance.colors[event.priority_tier],
    direction,
    motion: appearance.motion,
  };
}
