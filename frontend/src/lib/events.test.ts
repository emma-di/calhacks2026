import test from "node:test";
import assert from "node:assert/strict";
import {
  applyMock,
  emptyMock,
  expireMock,
  makeMock,
  parseSnapshot,
  request,
} from "./events.ts";

test("urgent cue interrupts; lower priority is recorded but cannot replace it", () => {
  let state = applyMock(emptyMock(), makeMock("knock"), 0);
  const alarm = makeMock("smoke_alarm");
  state = applyMock(state, alarm, 100);
  state = applyMock(state, makeMock("dog_bark"), 200);
  assert.equal(state.active?.event_id, alarm.event_id);
  assert.equal(state.decisions.at(-1)?.reason, "suppressed_lower_priority");
  assert.equal(expireMock(state, 30100).active, null);
});
test("tier zero never replaces active and duplicate IDs never extend lifetime", () => {
  const event = makeMock("knock");
  let state = applyMock(emptyMock(), event, 0);
  state = applyMock(state, makeMock("conversation"), 100);
  assert.equal(state.active?.event_id, event.event_id);
  assert.equal(state.decisions.at(-1)?.reason, "ignored_tier_zero");
  state = applyMock(state, event, 500);
  assert.equal(state.expiresAt, 3000);
  assert.equal(state.events.length, 2);
});
test("receiver state accepts nullable confidence but rejects malformed or out-of-range data", () => {
  const event = makeMock("name_called");
  assert.equal(
    parseSnapshot({ active: event, events: [event], decisions: [] }).active
      ?.confidence,
    null,
  );
  for (const change of [
    { priority_tier: 9 },
    { confidence: NaN },
    { type: "unknown" },
    { event_id: null },
  ]) {
    assert.throws(() =>
      parseSnapshot({
        active: { ...event, ...change },
        events: [],
        decisions: [],
      }),
    );
  }
  assert.throws(() => parseSnapshot({ events: [], decisions: [] }));
});
test("non-success HTTP response is an error, not a connected empty state", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response("Unavailable", { status: 503 });
  try {
    await assert.rejects(request("/state"), /503/);
  } finally {
    globalThis.fetch = original;
  }
});

test("preset defaults remain separate from explicit tier-zero overrides", async () => {
  const { mockPriority } = await import("./presets.ts");
  assert.equal(mockPriority("dog_bark", "active", {}), 2);
  assert.equal(mockPriority("dog_bark", "gentle", {}), 0);
  assert.equal(mockPriority("dog_bark", "active", { dog_bark: 0 }), 0);
  assert.equal(mockPriority("knock", "balanced", {}), 2);
});
