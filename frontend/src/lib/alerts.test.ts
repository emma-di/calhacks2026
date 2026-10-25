import test from "node:test";
import assert from "node:assert/strict";
import scenarios from "../../../audio/alert-scenarios.json";
import { AlertEngine, presets } from "./alerts.ts";
import { soundCatalog, type EventType } from "./events.ts";
import { AWARE_PRESET_DEFAULTS } from "../../mana/AwareOnboarding.jsx";
import { explain } from "./explain.ts";

const fixtureEvent = (type: EventType, id: string, at: number, direction?: [number, number], customId?: string) => {
  // A user-taught sound isn't in the catalog: its label and tier come from the user.
  const sound = soundCatalog.find((s) => s.type === type) ?? { label: customId ?? "Custom sound", tier: 2 };
  const custom = type === "custom" ? { custom_sound_id: customId } : {};
  return {
    schema_version: 1,
    event_id: id,
    type,
    label: sound.label,
    confidence: null,
    source: "mock",
    priority_tier: sound.tier,
    timestamp_ms: at,
    direction_degrees: direction?.[0] ?? null,
    direction_confidence: direction?.[1] ?? null,
    distance_meters: null,
    ...custom,
  };
};

test("browser simulator passes the same scenarios as the Python receiver", () => {
  for (const scenario of scenarios.scenarios) {
    const engine = new AlertEngine();
    if ("profile" in scenario) engine.prefs = {...scenario.profile, custom_sound_tiers:Object.fromEntries(((scenario as any).custom_sound_requests ?? []).map((sound:any) => [sound.id,sound.tier]))} as never;
    scenario.steps.forEach((step: Record<string, any>, index) => {
      const label = `${scenario.name} / step ${index}`;
      let result: Record<string, unknown> = {};
      if (step.add)
        result = { ...engine.add({...fixtureEvent(step.add, step.id, step.at, step.direction, step.sound), ...(step.target ? {target_event_id: step.target} : {})}, step.at) };
      else if (step.look) result = { resolved: engine.look(step.at, step.look) };
      else if (step.dismiss) {
        result = { dismissed: engine.dismiss(step.at, step.dismiss) };
        const last = engine.decisions.at(-1);
        if (last && last.at_ms === step.at) result.reason = last.reason;
      } else if (step.evidence) engine.observeSound(step.evidence.type, step.evidence.present, step.evidence.source, step.at);
      else if (step.controls) engine.setControls(step.at, step.controls);
      else engine.tick(step.at);
      const snap = engine.snapshot(step.at);
      const expect = step.expect;
      if ("active" in expect)
        assert.equal(snap.active?.event_id ?? null, expect.active, label);
      if ("reason" in expect) assert.equal(result.reason, expect.reason, label);
      if ("replaced" in expect) assert.equal(result.active_type, expect.replaced, label);
      if ("tier" in expect) assert.equal(result.priority_tier, expect.tier, label);
      if ("dismissed" in expect) assert.equal(result.dismissed, expect.dismissed, label);
      if ("queue" in expect)
        assert.deepEqual(snap.queue.map((q) => q.event_id), expect.queue, label);
      if ("remaining" in expect) assert.equal(snap.remaining_ms, expect.remaining, label);
      if ("sequence" in expect) assert.equal(snap.state_sequence, expect.sequence, label);
      if ("resolved" in expect) assert.equal(result.resolved, expect.resolved, label);
      if ("direction" in expect) assert.equal(snap.direction, expect.direction, label);
      if ("confirm" in expect) assert.equal(snap.confirm !== null, expect.confirm, label);
      if ("last_reason" in expect) assert.equal(snap.decisions.at(-1)?.reason, expect.last_reason, label);
      if ("events" in expect) assert.equal(snap.events.length, expect.events, label);
    });
  }
});

test("shared presets match the Mana onboarding defaults", () => {
  assert.deepEqual(presets, AWARE_PRESET_DEFAULTS);
});

test("every engine decision has a plain-language explanation", () => {
  const reasons = [
    "displayed", "interrupted", "queued", "resumed_from_queue", "expired_in_queue",
    "dropped_queue_full", "merged_repeat", "acknowledged_repeat", "dismissed", "duplicate",
    "paused", "ignored_tier_zero", "suppressed_lower_priority", "held_work_mode", "held_dnd_mode",
    "expired", "resolved_looked", "gesture_ignored", "gesture_waiting", "dismissed_gesture",
  ];
  for (const reason of reasons) {
    const text = explain({ event_id: "a", type: "knock", priority_tier: 2, reason, active_type: "smoke_alarm" });
    assert.ok(text.length > 8 && !text.includes("_"), reason);
  }
});

test("manual reset clears acknowledgement so a retest always shows", () => {
  const engine = new AlertEngine();
  engine.add(fixtureEvent("smoke_alarm", "s1", 0), 0);
  engine.dismiss(10, "s1");
  engine.reset(20);
  assert.equal(engine.add(fixtureEvent("smoke_alarm", "s2", 30), 30).reason, "displayed");
});
