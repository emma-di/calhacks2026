export type Tier = 0 | 1 | 2 | 3 | 4;
export type EventType =
  | "knock"
  | "bell"
  | "dog_bark"
  | "name_called"
  | "smoke_alarm"
  | "conversation"
  | "siren"
  | "alarm_clock"
  | "bicycle_bell";
export interface SoundEvent {
  schema_version: number;
  event_id: string;
  type: EventType;
  label: string;
  confidence: number | null;
  source: string;
  priority_tier: Tier;
  timestamp_ms: number;
  direction_degrees: number | null;
  direction_confidence: number | null;
  distance_meters: number | null;
}
export interface Decision {
  event_id: string;
  type: string;
  reason: string;
  priority_tier: Tier;
}
export interface Snapshot {
  active: SoundEvent | null;
  events: SoundEvent[];
  decisions: Decision[];
}
export const tierNames = [
  "Ignore",
  "Ambient",
  "Notify",
  "Attention",
  "Urgent",
] as const;
export const lifetime: Record<Tier, number> = {
  0: 0,
  1: 2000,
  2: 3000,
  3: 5000,
  4: 30000,
};
export const sounds: {
  type: EventType;
  label: string;
  detail: string;
  tier: Tier;
  receiver: boolean;
}[] = [
  {
    type: "knock",
    label: "Door knock",
    detail: "Someone at the door",
    tier: 2,
    receiver: true,
  },
  {
    type: "bell",
    label: "Bell / chime",
    detail: "A little heads-up",
    tier: 2,
    receiver: true,
  },
  {
    type: "dog_bark",
    label: "Dog barking",
    detail: "Around you",
    tier: 1,
    receiver: true,
  },
  {
    type: "name_called",
    label: "Your name",
    detail: "An invitation to connect",
    tier: 3,
    receiver: false,
  },
  {
    type: "smoke_alarm",
    label: "Smoke alarm",
    detail: "An important warning",
    tier: 4,
    receiver: true,
  },
  {
    type: "conversation",
    label: "Conversation",
    detail: "Let the background stay there",
    tier: 0,
    receiver: false,
  },
];
export const soundCatalog = [
  ...sounds,
  {
    type: "alarm_clock" as EventType,
    label: "Alarm clock",
    detail: "A scheduled reminder",
    tier: 2 as Tier,
    receiver: true,
  },
  {
    type: "siren" as EventType,
    label: "Siren",
    detail: "An approaching warning",
    tier: 3 as Tier,
    receiver: true,
  },
];
export function makeMock(type: EventType, tier?: Tier): SoundEvent {
  const sound = soundCatalog.find((s) => s.type === type)!;
  return {
    schema_version: 1,
    event_id: crypto.randomUUID(),
    type,
    label: sound.label,
    confidence: null,
    source: "mock",
    priority_tier: tier ?? sound.tier,
    timestamp_ms: Date.now(),
    direction_degrees: null,
    direction_confidence: null,
    distance_meters: null,
  };
}
// Browser-only simulator. Receiver mode delegates ALL selection and timing to Python.
export interface MockState extends Snapshot {
  expiresAt: number;
}
export const emptyMock = (): MockState => ({
  active: null,
  events: [],
  decisions: [],
  expiresAt: 0,
});
export function expireMock(state: MockState, now: number): MockState {
  return state.active && now >= state.expiresAt
    ? { ...state, active: null, expiresAt: 0 }
    : state;
}
export function applyMock(
  state: MockState,
  event: SoundEvent,
  now: number,
): MockState {
  state = expireMock(state, now);
  if (state.events.some((e) => e.event_id === event.event_id)) return state;
  const tier = event.priority_tier;
  const show =
    tier > 0 && (!state.active || tier >= state.active.priority_tier);
  const reason =
    tier === 0
      ? "ignored_tier_zero"
      : show
        ? "displayed"
        : "suppressed_lower_priority";
  return {
    active: show ? event : state.active,
    expiresAt: show ? now + lifetime[tier] : state.expiresAt,
    events: [...state.events, event].slice(-50),
    decisions: [
      ...state.decisions,
      {
        event_id: event.event_id,
        type: event.type,
        priority_tier: tier,
        reason,
      },
    ].slice(-50),
  };
}
const knownTypes = new Set([
  "knock",
  "bell",
  "dog_bark",
  "name_called",
  "smoke_alarm",
  "conversation",
  "siren",
  "alarm_clock",
  "bicycle_bell",
]);
export function parseEvent(input: unknown): SoundEvent {
  if (!input || typeof input !== "object") throw new Error("Invalid event");
  const e = input as Record<string, unknown>;
  if (
    e.schema_version !== 1 ||
    typeof e.event_id !== "string" ||
    !e.event_id ||
    typeof e.label !== "string" ||
    !knownTypes.has(String(e.type)) ||
    typeof e.source !== "string" ||
    !Number.isInteger(e.priority_tier) ||
    Number(e.priority_tier) < 0 ||
    Number(e.priority_tier) > 4 ||
    typeof e.timestamp_ms !== "number" ||
    !Number.isInteger(e.timestamp_ms) ||
    e.timestamp_ms < 0 ||
    !(
      e.confidence === null ||
      (typeof e.confidence === "number" &&
        Number.isFinite(e.confidence) &&
        e.confidence >= 0 &&
        e.confidence <= 1)
    )
  ) {
    throw new Error("Receiver returned an invalid event");
  }
  // No spatial rendering until a validated adapter and coordinate frame are agreed.
  return {
    ...e,
    direction_degrees: null,
    direction_confidence: null,
    distance_meters: null,
  } as unknown as SoundEvent;
}
export function parseSnapshot(input: unknown): Snapshot {
  if (!input || typeof input !== "object")
    throw new Error("Invalid receiver state");
  const s = input as Record<string, unknown>;
  if (
    !Array.isArray(s.events) ||
    !Array.isArray(s.decisions) ||
    !("active" in s)
  )
    throw new Error("Invalid receiver state");
  const decisions = s.decisions.map((d) => {
    if (
      !d ||
      typeof d !== "object" ||
      typeof d.event_id !== "string" ||
      typeof d.reason !== "string" ||
      typeof d.type !== "string" ||
      !Number.isInteger(d.priority_tier) ||
      d.priority_tier < 0 ||
      d.priority_tier > 4
    )
      throw new Error("Invalid decision");
    return d as Decision;
  });
  return {
    active: s.active === null ? null : parseEvent(s.active),
    events: s.events.map(parseEvent),
    decisions,
  };
}
export async function request(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<unknown> {
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? "GET" : "POST",
    ...(body === undefined
      ? {}
      : {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
    signal: signal ?? AbortSignal.timeout(3000),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Receiver returned ${response.status}`);
  return response.json();
}
