import { soundCatalog, type EventType, type Tier } from "./events";
export type Preset = "gentle" | "balanced" | "active";
import { AWARE_PRESET_DEFAULTS } from "../../mana/AwareOnboarding.jsx";
const presets = AWARE_PRESET_DEFAULTS;
export function mockPriority(
  type: EventType,
  preset: Preset,
  overrides: Partial<Record<EventType, Tier>>,
): Tier {
  return (
    overrides[type] ??
    presets[preset][type] ??
    soundCatalog.find((sound) => sound.type === type)?.tier ??
    0
  );
}
