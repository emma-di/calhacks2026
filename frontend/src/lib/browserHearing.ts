// Listening in the browser for the public demo (no receiver): sounds are recognized on this device by
// MediaPipe's YAMNet; names and questions come from the browser's speech recognition service, which in
// Chrome sends speech to Google. The laptop setup (audio/cli.py) keeps everything on the laptop instead.
// Rules mirror the receiver: audio/policy-yamnet.json, audio/names.py and audio/questions.py.
import policy from "../../../audio/policy-yamnet.json";
import type { SoundEvent, Tier } from "./events";

export const COOLDOWN_MS = 5000;
export const WINDOW_SAMPLES = 15600; // YAMNet hears 0.975 s at 16 kHz

type Rule = { labels: Record<string, number>; threshold: number; enabled?: boolean };
// Bicycle bell stays disabled pending evidence (AGENTS.md); snap is a gesture, not an alert.
const RULES = Object.entries(policy.rules as Record<string, Rule>).filter(
  ([type, rule]) => rule.enabled !== false && type !== "bicycle_bell" && type !== "finger_snap",
);
const TIERS: Record<string, Tier> = { knock: 2, dog_bark: 1, siren: 3, smoke_alarm: 4, alarm_clock: 2 };
const LABELS: Record<string, string> = {
  knock: "Door knock", dog_bark: "Dog barking", siren: "Siren", smoke_alarm: "Fire / smoke alarm", alarm_clock: "Alarm clock",
};

export interface PickedSound {
  id: string;
  label: string;
  tier: number;
  status?: string;
  model_labels?: string[];
  threshold?: number;
  icon_id?: string;
  icon?: string;
}

const base = (type: string, label: string, tier: number, at: number) => ({
  schema_version: 1, event_id: crypto.randomUUID(), type, label, confidence: null as number | null,
  source: "microphone", priority_tier: tier as Tier, timestamp_ms: at,
  direction_degrees: null, direction_confidence: null, distance_meters: null,
});

/** Alerts for one classified window. last holds the time each sound last alerted (cooldown). */
export function detectSounds(scores: Map<string, number>, picked: PickedSound[], last: Map<string, number>, now: number): SoundEvent[] {
  const events: SoundEvent[] = [];
  const fire = (key: string, make: () => SoundEvent) => {
    if (now - (last.get(key) ?? -Infinity) < COOLDOWN_MS) return;
    last.set(key, now);
    events.push(make());
  };
  for (const [type, rule] of RULES) {
    const score = Math.max(...Object.entries(rule.labels).map(([label, weight]) => (scores.get(label) ?? 0) * weight));
    if (score >= rule.threshold)
      fire(type, () => ({ ...base(type, LABELS[type] ?? type, TIERS[type] ?? 2, now), confidence: score }) as SoundEvent);
  }
  for (const sound of picked) {
    if (sound.status !== "recognized" || !sound.model_labels?.length) continue;
    const score = Math.max(...sound.model_labels.map((label) => scores.get(label) ?? 0));
    if (score >= (sound.threshold ?? 0.15))
      fire(`custom:${sound.id}`, () => ({
        ...base("custom", sound.label, sound.tier, now), confidence: score,
        custom_sound_id: sound.id, icon_id: sound.icon_id ?? sound.icon,
      }) as SoundEvent);
  }
  return events;
}

// Same phrases as audio/names.py.
export const ATTENTION_PHRASES = ["hey you", "excuse me", "hello", "over here", "come here", "get over here", "hey there", "pardon me", "hey"];
export const WARNING_PHRASES = ["watch out", "look out"];

const words = (text: string) => ` ${text.toLowerCase().replace(/[^a-z0-9' ]+/g, " ").replace(/\s+/g, " ").trim()} `;

/** Which call a transcript contains: your name first, then a warning, then an attention call. */
export function findCall(transcript: string, names: string[]): { alias: string; label: string; tier: Tier } | null {
  const said = words(transcript);
  const name = names.map((n) => n.trim()).filter(Boolean).find((n) => said.includes(words(n)));
  if (name) return { alias: "primary", label: "Your name", tier: 3 };
  const warning = WARNING_PHRASES.findIndex((p) => said.includes(` ${p} `));
  if (warning >= 0) return { alias: `warning-${warning}`, label: "Watch out!", tier: 4 };
  const call = ATTENTION_PHRASES.findIndex((p) => said.includes(` ${p} `));
  return call >= 0 ? { alias: `attention-${call}`, label: "Someone's calling", tier: 3 } : null;
}

// Same rules as audio/questions.py.
const QUESTION_STARTS = new Set(["what", "when", "where", "who", "whom", "whose", "why", "how", "which", "is", "are", "am",
  "were", "do", "does", "did", "can", "could", "will", "would", "should", "shall", "may"]);
const REQUEST_STARTS = ["please", "let me know", "tell me", "remember to", "don't forget", "dont forget", "make sure",
  "come", "grab", "bring", "hold on", "wait", "look", "listen", "help"];
const CALL_WORDS = ["hey you", "hey there", "excuse me", "pardon me", "hey", "hello", "hi", "yo", "oh", "so", "okay", "ok", "um", "uh", "er", "erm", "well"];

function stripCall(sentence: string, names: string[]) {
  const lead = [...CALL_WORDS, ...names.map((n) => n.toLowerCase())].filter(Boolean).sort((a, b) => b.length - a.length)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`^(?:${lead.join("|")})\\b[\\s,.!-]*`, "i");
  let previous = "";
  while (previous !== sentence) [previous, sentence] = [sentence, sentence.replace(pattern, "")];
  return sentence.trim();
}

function isQuestion(sentence: string) {
  const lowered = sentence.toLowerCase().trim();
  if (lowered.endsWith("?") || REQUEST_STARTS.some((r) => lowered === r || lowered.startsWith(`${r} `))) return true;
  const parts = lowered.split(/\s+/);
  return QUESTION_STARTS.has(parts[0].replace(/[^a-z]/g, "")) && parts.length >= 3;
}

/** The question or request in what was said, without the name in front, or null. */
export function directedQuestion(transcript: string, names: string[]): string | null {
  for (const sentence of transcript.trim().split(/(?<=[.?!])\s+/)) {
    const body = stripCall(sentence, names);
    if (body.split(/\s+/).length >= 2 && isQuestion(body)) {
      const first = body.split(/\s+/)[0].toLowerCase().replace(/[^a-z]/g, "");
      return QUESTION_STARTS.has(first) && !/[.?!]$/.test(body) ? `${body}?` : body;
    }
  }
  return null;
}

/** Short text the 5x7 OLED font can draw (audio/questions.py for_display). */
export function forDisplay(text: string, limit = 84) {
  let out = text.replace(/\b(um+|uh+|er+m?)\b,?\s*/gi, "").replace(/['’]/g, "")
    .replace(/[^A-Za-z0-9 !\-./?]+/g, " ").replace(/\s+/g, " ").trim();
  if (out.length > limit) out = out.slice(0, limit - 3).replace(/\s+\S*$/, "").replace(/[ .]+$/, "") + "...";
  return out.charAt(0).toUpperCase() + out.slice(1);
}

export function nameEvent(call: { alias: string; label: string; tier: Tier }, at: number): SoundEvent {
  return { ...base("name_called", call.label, call.tier, at), schema_version: 2, matched_alias_id: call.alias,
    profile_revision: 0 } as unknown as SoundEvent;
}

export function questionEvent(question: string, transcript: string, at: number): SoundEvent {
  return { ...base("question", forDisplay(question), 3, at), transcript: transcript.slice(0, 600),
    summary_source: "local" } as SoundEvent;
}
