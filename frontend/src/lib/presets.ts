import { soundCatalog, type EventType, type Tier } from "./events";
export type Preset = "gentle" | "balanced" | "active";
const presets: Record<Preset, Partial<Record<EventType, Tier>>> = {
  gentle: {
    conversation: 0,
    dog_bark: 0,
    knock: 1,
    bell: 1,
    name_called: 3,
    smoke_alarm: 4,
  },
  balanced: {},
  active: {
    conversation: 0,
    dog_bark: 2,
    knock: 3,
    bell: 3,
    name_called: 3,
    smoke_alarm: 4,
  },
};
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
