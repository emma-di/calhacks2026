import test from "node:test";
import assert from "node:assert/strict";
import { makeMock, parseSnapshot, request } from "./events.ts";

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

test("shared presentation keeps icons, urgent text and mock placement consistent", async () => {
  const { cuePresentation } = await import("./presentation.ts");
  const appearance = {
    text: "icons" as const,
    motion: "none" as const,
    direction: "left" as const,
    colors: { 0: "#fff", 1: "#fff", 2: "#fff", 3: "#fff", 4: "#fff" },
  };
  const bell = cuePresentation(makeMock("bell"), appearance, "left");
  assert.equal(bell?.icon, "bell");
  assert.equal(bell?.label, null);
  assert.equal(bell?.direction, "left");
  assert.equal(
    cuePresentation(makeMock("smoke_alarm"), appearance, "unknown")?.label,
    "Fire / smoke alarm",
  );
  assert.equal(
    cuePresentation(makeMock("dog_bark", 0), appearance, "left"),
    null,
  );
});

test("malformed receiver extensions fail cleanly instead of crashing the live screen", () => {
  const base = { active: null, events: [], decisions: [] };
  for (const extra of [
    { health: {} },
    { health: { display: {} } },
    { remaining_ms: NaN },
    { remaining_ms: -1 },
    { confirm: { direction: "north", remaining_ms: 50 } },
    { confirm: { direction: null, remaining_ms: Infinity } },
    { queue: [null] },
    { queue: [{ event_id: "x", type: "knock", tier: 9 }] },
    { state_sequence: Infinity },
  ])
    assert.throws(() => parseSnapshot({ ...base, ...extra }));
});

test("receiver display label setting is authoritative for the physical mirror", () => {
  const base = { active: null, events: [], decisions: [] };
  assert.equal(
    parseSnapshot({ ...base, display: { show_labels: false } }).display_labels,
    false,
  );
  assert.equal(
    parseSnapshot({ ...base, display: { show_labels: true } }).display_labels,
    true,
  );
  assert.equal(parseSnapshot(base).display_labels, null);
});

test("name events from John's spotter (schema v2) parse; other v2 events do not", () => {
  const name = makeMock("name_called");
  assert.equal(name.schema_version, 2);
  assert.equal(parseSnapshot({ active: name, events: [name], decisions: [] }).active?.type, "name_called");
  assert.throws(() =>
    parseSnapshot({ active: { ...makeMock("knock"), schema_version: 2 }, events: [], decisions: [] }),
  );
});
