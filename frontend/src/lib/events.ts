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
  active_type?: string | null;
}
export interface Snapshot {
  active: SoundEvent | null;
  events: SoundEvent[];
  decisions: Decision[];
}
export interface Health {
  display: { connected: boolean; clients: Record<string, number> };
  capture: { live: boolean; last_event_ms_ago: Record<string, number> };
  name_worker: string;
  spatial: string;
}
// What every view renders, from either the browser engine or the receiver.
export interface ViewState extends Snapshot {
  remaining_ms: number;
  state_sequence: number;
  focus_mode: "everyday" | "work" | "dnd";
  paused: boolean;
  queue: { event_id: string; type: EventType; tier: Tier }[];
  health: Health | null;
  session_id: string | null;
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
    receiver: true,
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
export function parseSnapshot(input: unknown): ViewState {
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
  const focus = ["everyday", "work", "dnd"].includes(String(s.focus_mode))
    ? (s.focus_mode as ViewState["focus_mode"])
    : "everyday";
  return {
    active: s.active === null ? null : parseEvent(s.active),
    events: s.events.map(parseEvent),
    decisions,
    remaining_ms: typeof s.remaining_ms === "number" ? s.remaining_ms : 0,
    state_sequence: typeof s.state_sequence === "number" ? s.state_sequence : 0,
    focus_mode: focus,
    paused: s.paused === true,
    queue: Array.isArray(s.queue) ? (s.queue as ViewState["queue"]) : [],
    health: s.health && typeof s.health === "object" ? (s.health as Health) : null,
    session_id: typeof s.session_id === "string" ? s.session_id : null,
  };
}
export async function request(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
  method?: "PUT",
): Promise<unknown> {
  const response = await fetch(`/api${path}`, {
    method: method ?? (body === undefined ? "GET" : "POST"),
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
