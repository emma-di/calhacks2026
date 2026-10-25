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
  | "bicycle_bell"
  | "finger_snap"
  | "thumbs_up"
  | "custom";
export interface SoundEvent {
  target_event_id?: string;
  matched_alias_id?: string;
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
  // Present only on type "custom": which user-taught sound (label is the user's own name for it).
  custom_sound_id?: string;
  icon_id?: string; // a custom sound may pick its glasses icon (falls back to the policy icon)
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
  capture: {
    live: boolean;
    last_event_ms_ago: Record<string, number>;
    listening?: boolean;
    listening_source?: string | null;
  };
  name_worker: string;
  spatial: string | { connected: boolean; devices: Record<string, { age_ms: number; bearing_degrees: number | null; coherence: number; calibrated: boolean }> };
}
// One recognizer analysis window (audio/observations.py, John's format): what it heard and why.
export interface Observation {
  seq: number;
  source: string;
  received_ms: number;
  level_dbfs: number;
  top: { label: string; score: number }[];
  rules: Record<string, { score: number; threshold: number; reason: string }>;
  emitted: { event_id: string; type: string; label: string }[];
}
// What every view renders, from either the browser engine or the receiver.
export interface ViewState extends Snapshot {
  display_labels: boolean | null;
  remaining_ms: number;
  direction: "front" | "right" | "behind" | "left" | null;
  confirm: {
    direction: "front" | "right" | "behind" | "left" | null;
    remaining_ms: number;
  } | null;
  state_sequence: number;
  focus_mode: "everyday" | "work" | "dnd";
  paused: boolean;
  repeat_suppression?: boolean;
  snap_to_dismiss?: boolean;
  queue: { event_id: string; type: EventType; tier: Tier }[];
  health: Health | null;
  session_id: string | null;
  observations: Observation[];
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
    label: "Fire / smoke alarm",
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
  {
    type: "finger_snap" as EventType,
    label: "Finger snap",
    detail: "Dismisses the cue that is showing (audio, disabled)",
    tier: 0 as Tier,
    receiver: true,
  },
  {
    type: "thumbs_up" as EventType,
    label: "Thumbs up",
    detail: "Dismisses the cue that is showing (camera)",
    tier: 0 as Tier,
    receiver: true,
  },
];
// A simulated direction is labeled as a test sound and carries full confidence.
export function makeMock(
  type: EventType,
  tier?: Tier,
  directionDegrees: number | null = null,
): SoundEvent {
  const sound = soundCatalog.find((s) => s.type === type)!;
  if (type === "name_called")
    // John's name events are schema v2 (audio/names.py): no score, which alias matched. Direction
    // comes from the Pi stereo pair like every other cue.
    return {
      schema_version: 2,
      event_id: crypto.randomUUID(),
      type,
      label: sound.label,
      confidence: null,
      source: "mock",
      priority_tier: tier ?? sound.tier,
      timestamp_ms: Date.now(),
      direction_degrees: directionDegrees,
      direction_confidence: directionDegrees === null ? null : 1,
      distance_meters: null,
      matched_alias_id: "primary",
      profile_revision: 0,
    } as SoundEvent;
  return {
    schema_version: 1,
    event_id: crypto.randomUUID(),
    type,
    label: sound.label,
    confidence: null,
    source: "mock",
    priority_tier: tier ?? sound.tier,
    timestamp_ms: Date.now(),
    direction_degrees: directionDegrees,
    direction_confidence: directionDegrees === null ? null : 1,
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
  "finger_snap",
  "thumbs_up",
  "custom",
]);
export function parseEvent(input: unknown): SoundEvent {
  if (!input || typeof input !== "object") throw new Error("Invalid event");
  const e = input as Record<string, unknown>;
  if (
    !(e.schema_version === 1 || (e.schema_version === 2 && e.type === "name_called")) ||
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
  if (e.type === "custom" && !(typeof e.custom_sound_id === "string" && e.custom_sound_id.length > 0 && e.custom_sound_id.length <= 120))
    throw new Error("Receiver returned a custom sound without an id");
  // Direction is kept only as a validated pair; the engine decides whether it is confident enough.
  const degrees = e.direction_degrees;
  const certainty = e.direction_confidence;
  const directed =
    typeof degrees === "number" &&
    Number.isFinite(degrees) &&
    Math.abs(degrees) <= 180 &&
    typeof certainty === "number" &&
    certainty >= 0 &&
    certainty <= 1;
  return {
    ...e,
    direction_degrees: directed ? degrees : null,
    direction_confidence: directed ? certainty : null,
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
  const nonnegative = (value: unknown, name: string, fallback = 0): number => {
    if (value === undefined) return fallback;
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0)
      throw new Error(`Invalid ${name}`);
    return value;
  };
  const directions = ["front", "right", "behind", "left"];
  let confirm: ViewState["confirm"] = null;
  if (s.confirm !== undefined && s.confirm !== null) {
    if (typeof s.confirm !== "object") throw new Error("Invalid confirmation");
    const c = s.confirm as Record<string, unknown>;
    if (c.direction !== null && !directions.includes(String(c.direction)))
      throw new Error("Invalid confirmation direction");
    confirm = {
      direction: c.direction as ViewState["direction"],
      remaining_ms: nonnegative(c.remaining_ms, "confirmation lifetime"),
    };
  }
  const queue: ViewState["queue"] = [];
  if (s.queue !== undefined) {
    if (!Array.isArray(s.queue) || s.queue.length > 5)
      throw new Error("Invalid queue");
    for (const item of s.queue) {
      if (
        !item ||
        typeof item.event_id !== "string" ||
        !knownTypes.has(item.type) ||
        !Number.isInteger(item.tier) ||
        item.tier < 0 ||
        item.tier > 4
      )
        throw new Error("Invalid queued cue");
      queue.push(item);
    }
  }
  let health: Health | null = null;
  if (s.health !== undefined && s.health !== null) {
    const h = s.health as Health;
    if (
      !h.display ||
      typeof h.display.connected !== "boolean" ||
      !h.capture ||
      typeof h.capture.live !== "boolean"
    )
      throw new Error("Invalid receiver health");
    health = h;
  }
  const focus = ["everyday", "work", "dnd"].includes(String(s.focus_mode))
    ? (s.focus_mode as ViewState["focus_mode"])
    : "everyday";
  return {
    display_labels:
      s.display &&
      typeof s.display === "object" &&
      typeof (s.display as { show_labels?: unknown }).show_labels === "boolean"
        ? (s.display as { show_labels: boolean }).show_labels
        : null,
    active: s.active === null ? null : parseEvent(s.active),
    events: s.events.map(parseEvent),
    decisions,
    remaining_ms: nonnegative(s.remaining_ms, "remaining lifetime"),
    direction: ["front", "right", "behind", "left"].includes(
      String(s.direction),
    )
      ? (s.direction as ViewState["direction"])
      : null,
    state_sequence: nonnegative(s.state_sequence, "state sequence"),
    confirm,
    focus_mode: focus,
    paused: s.paused === true,
    repeat_suppression: s.repeat_suppression !== false,
    snap_to_dismiss: s.snap_to_dismiss === true,
    queue,
    health,
    session_id: typeof s.session_id === "string" ? s.session_id : null,
    // Diagnostics only: malformed reports are dropped rather than failing the whole state.
    observations: Array.isArray(s.observations)
      ? (s.observations as Observation[])
          .filter(
            (o) =>
              o && typeof o === "object" && Array.isArray(o.top) && typeof o.level_dbfs === "number" &&
              o.rules && typeof o.rules === "object" && Array.isArray(o.emitted),
          )
          .slice(-10)
      : [],
  };
}
export async function request(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
  method?: "GET" | "PUT",
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
