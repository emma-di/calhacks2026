// Line-for-line port of audio/alerts.py for the browser simulator. Receiver mode never runs this:
// Python is authoritative there. Both engines replay audio/alert-scenarios.json in their tests.
import policy from "../../../audio/alert-policy.json";
import type { EventType, SoundEvent, Tier } from "./events";

export type FocusMode = "everyday" | "work" | "dnd";
export type Preset = keyof typeof policy.presets;
export interface Preferences {
  mode: Preset;
  event_tiers: Partial<Record<EventType, Tier>>;
}
export interface AlertDecision {
  event_id: string;
  type: EventType;
  priority_tier: Tier;
  reason: string;
  at_ms: number;
  active_type: EventType | null;
  shown_event_id?: string;
  direction?: Direction;
  gesture?: string;
}
export interface LoggedEvent extends SoundEvent {
  producer_tier?: Tier;
}
interface Active {
  event: LoggedEvent;
  tier: Tier;
  started: number;
  expires: number;
  repeats: number;
  direction: Direction | null;
}
interface Queued {
  event: LoggedEvent;
  tier: Tier;
  received: number;
}
export interface EngineSnapshot {
  active: LoggedEvent | null;
  events: LoggedEvent[];
  decisions: AlertDecision[];
  state_sequence: number;
  remaining_ms: number;
  direction: Direction | null;
  confirm: { direction: Direction | null; remaining_ms: number } | null;
  focus_mode: FocusMode;
  paused: boolean;
  queue: { event_id: string; type: EventType; tier: Tier }[];
}

const lifetime = (tier: Tier) =>
  policy.lifetime_ms[String(tier) as keyof typeof policy.lifetime_ms];
export const presets = policy.presets as Record<
  Preset,
  Partial<Record<EventType, Tier>>
>;
export const GESTURES = new Set<string>(["thumbs_up", "finger_snap"]); // wearer input, never an alert
export const focusMinimum = policy.focus_minimum_tier as Record<
  FocusMode,
  Tier
>;

// Each side covers 90 degrees and puts the cue on that edge. A two-microphone worker cannot tell
// front from behind and should send null rather than guess.
export type Direction = "front" | "right" | "behind" | "left";
export const directionDegrees: Record<Direction, number> = {
  front: 0,
  right: 90,
  behind: 180,
  left: -90,
};

export function directionBucket(
  degrees: number | null,
  confidence: number | null,
): Direction | null {
  if (
    degrees === null ||
    confidence === null ||
    confidence < policy.direction_min_confidence
  )
    return null;
  const d = ((((degrees + 180) % 360) + 360) % 360) - 180;
  if (d >= -45 && d <= 45) return "front";
  if (d > 45 && d <= 135) return "right";
  if (d >= -135 && d < -45) return "left";
  return "behind";
}

export function effectiveTier(
  type: EventType,
  producer: Tier,
  prefs: Preferences,
): Tier {
  return prefs.event_tiers[type] ?? presets[prefs.mode][type] ?? producer;
}

export class AlertEngine {
  prefs: Preferences = { mode: "balanced", event_tiers: {} };
  focusMode: FocusMode = "everyday";
  paused = false;
  sequence = 0;
  active: Active | null = null;
  queue: Queued[] = [];
  acks = new Map<EventType, number>();
  gestures: number[] = [];
  confirm: {
    until: number;
    direction: Direction | null;
    event_id: string;
  } | null = null;
  seen: string[] = [];
  events: LoggedEvent[] = [];
  decisions: AlertDecision[] = [];

  private decide(
    event: LoggedEvent,
    tier: Tier,
    reason: string,
    now: number,
    extra: Partial<AlertDecision> = {},
  ): AlertDecision {
    const decision: AlertDecision = {
      event_id: event.event_id,
      type: event.type,
      priority_tier: tier,
      reason,
      at_ms: Math.round(now),
      active_type: this.active?.event.type ?? null,
      ...extra,
    };
    this.decisions = [...this.decisions, decision].slice(-50);
    return decision;
  }
  private show(event: LoggedEvent, tier: Tier, now: number) {
    this.active = {
      event,
      tier,
      started: now,
      expires: now + lifetime(tier),
      repeats: 0,
      direction: directionBucket(
        event.direction_degrees,
        event.direction_confidence,
      ),
    };
    this.sequence += 1;
  }
  private clear() {
    if (this.active) {
      this.active = null;
      this.sequence += 1;
    }
  }
  private freshQueue(now: number) {
    this.queue = this.queue.filter((item) => {
      if (now - item.received <= policy.queue_fresh_ms) return true;
      this.decide(item.event, item.tier, "expired_in_queue", now);
      return false;
    });
  }
  private boundQueue(now: number) {
    while (this.queue.length > policy.queue_limit) {
      const dropped = this.best(this.queue, (b, a) =>
        b.tier !== a.tier ? b.tier < a.tier : b.received < a.received,
      );
      this.queue = this.queue.filter((item) => item !== dropped);
      this.decide(dropped.event, dropped.tier, "dropped_queue_full", now);
    }
  }
  private blocked(tier: Tier) {
    return tier < focusMinimum[this.focusMode];
  }
  private best(items: Queued[], pick: (a: Queued, b: Queued) => boolean) {
    return items.reduce((a, b) => (pick(b, a) ? b : a));
  }

  // The wearer dealt with the cue: acknowledge its sound, confirm with a check, then resume.
  private resolve(
    now: number,
    reason: string,
    extra: Partial<AlertDecision> = {},
  ): AlertDecision {
    const active = this.active!;
    this.acks.set(active.event.type, now + policy.acknowledge_hold_ms);
    const decision = this.decide(active.event, active.tier, reason, now, extra);
    this.confirm = {
      until: now + policy.confirm_ms,
      direction: active.direction,
      event_id: active.event.event_id,
    };
    this.gestures = [];
    this.clear();
    this.tick(now);
    return decision;
  }

  // A thumbs-up (camera) or snap dismisses the showing cue; with nothing showing it does nothing.
  private gesture(event: SoundEvent, now: number): AlertDecision {
    const extra = { gesture: event.type };
    if (!this.active)
      return this.decide(event, 0, "gesture_ignored", now, extra);
    const rule = policy.gesture_to_dismiss;
    this.gestures = [
      ...this.gestures.filter((t) => now - t <= rule.window_ms),
      now,
    ];
    if (this.gestures.length < rule.count)
      return this.decide(event, 0, "gesture_waiting", now, extra);
    return this.resolve(now, "dismissed_gesture", extra);
  }

  tick(now: number) {
    if (this.active && now >= this.active.expires) {
      this.decide(this.active.event, this.active.tier, "expired", now);
      this.clear();
    }
    if (this.confirm && now >= this.confirm.until) {
      this.confirm = null;
      this.sequence += 1;
    }
    this.freshQueue(now);
    if (!this.active && this.queue.length && !this.confirm) {
      const best = this.best(this.queue, (b, a) =>
        b.tier !== a.tier ? b.tier > a.tier : b.received > a.received,
      );
      this.queue = this.queue.filter((item) => item !== best);
      this.show(best.event, best.tier, now);
      this.decide(best.event, best.tier, "resumed_from_queue", now);
    }
  }

  add(event: SoundEvent, now: number): AlertDecision {
    this.tick(now);
    if (this.seen.includes(event.event_id))
      return this.decide(event, event.priority_tier, "duplicate", now);
    this.seen = [...this.seen, event.event_id].slice(-256);
    if (GESTURES.has(event.type)) return this.gesture(event, now);
    const producer = event.priority_tier;
    const tier = effectiveTier(event.type, producer, this.prefs);
    const logged: LoggedEvent = {
      ...event,
      priority_tier: tier,
      producer_tier: producer,
    };
    this.events = [...this.events, logged].slice(-50);
    const kind = event.type;
    if (this.paused) return this.decide(logged, tier, "paused", now);
    if (tier === 0) return this.decide(logged, tier, "ignored_tier_zero", now);
    if (this.blocked(tier))
      return this.decide(logged, tier, `held_${this.focusMode}_mode`, now);
    if (now < (this.acks.get(kind) ?? -1)) {
      this.acks.set(kind, now + policy.acknowledge_hold_ms);
      return this.decide(logged, tier, "acknowledged_repeat", now);
    }
    const active = this.active;
    if (active && active.event.type === kind && tier <= active.tier) {
      active.repeats += 1;
      if (active.tier === 4) {
        const cap = active.started + policy.urgent_ongoing_cap_ms;
        const extended = Math.min(
          cap,
          Math.max(active.expires, now + lifetime(4)),
        );
        if (extended > active.expires) {
          active.expires = extended;
          this.sequence += 1;
        }
      }
      return this.decide(logged, tier, "merged_repeat", now, {
        shown_event_id: active.event.event_id,
      });
    }
    if (!active || tier >= active.tier) {
      const reason = active ? "interrupted" : "displayed";
      this.queue = this.queue.filter((item) => item.event.type !== kind);
      if (
        active &&
        (active.tier === 2 || active.tier === 3) &&
        active.event.type !== kind
      )
        this.queue.push({
          event: active.event,
          tier: active.tier,
          received: active.started,
        });
      this.boundQueue(now);
      this.show(logged, tier, now);
      return this.decide(logged, tier, reason, now, {
        active_type: active ? active.event.type : null,
      });
    }
    if (tier === 1)
      return this.decide(logged, tier, "suppressed_lower_priority", now);
    this.queue = this.queue.filter((item) => item.event.type !== kind);
    this.queue.push({ event: logged, tier, received: now });
    this.boundQueue(now);
    return this.decide(logged, tier, "queued", now);
  }

  dismiss(now: number, eventId?: string): boolean {
    this.tick(now);
    if (!this.active) return false;
    const shown = this.active.event;
    if (eventId !== undefined && eventId !== shown.event_id) return false;
    this.resolve(now, "dismissed");
    return true;
  }

  // The wearer turned toward the sound (a head-orientation source, or the simulated control).
  look(now: number, direction: Direction): boolean {
    this.tick(now);
    if (!this.active || this.active.direction !== direction) return false;
    this.resolve(now, "resolved_looked", { direction });
    return true;
  }

  setControls(
    now: number,
    changes: { focus_mode?: FocusMode; paused?: boolean },
  ) {
    this.tick(now);
    if (changes.focus_mode !== undefined) this.focusMode = changes.focus_mode;
    if (changes.paused !== undefined) this.paused = changes.paused;
    if (this.paused) {
      this.queue = [];
      if (this.confirm) {
        this.confirm = null;
        this.sequence += 1;
      }
      this.clear();
      return;
    }
    this.queue = this.queue.filter((item) => !this.blocked(item.tier));
    if (this.active && this.blocked(this.active.tier)) {
      this.clear();
      this.tick(now);
    }
  }

  // A manual sound test starts from a clean slate so the previous sample cannot hide it.
  reset(now: number) {
    this.tick(now);
    this.queue = [];
    this.acks.clear();
    this.confirm = null;
    this.gestures = [];
    this.clear();
  }

  snapshot(now: number): EngineSnapshot {
    this.tick(now);
    return {
      active: this.active?.event ?? null,
      events: this.events,
      decisions: this.decisions,
      state_sequence: this.sequence,
      remaining_ms: this.active
        ? Math.max(0, Math.round(this.active.expires - now))
        : 0,
      direction: this.active?.direction ?? null,
      confirm: this.confirm
        ? {
            direction: this.confirm.direction,
            remaining_ms: Math.round(this.confirm.until - now),
          }
        : null,
      focus_mode: this.focusMode,
      paused: this.paused,
      queue: this.queue.map((item) => ({
        event_id: item.event.event_id,
        type: item.event.type,
        tier: item.tier,
      })),
    };
  }
}
