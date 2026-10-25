import test from "node:test";
import assert from "node:assert/strict";
import { ProfileEdits } from "./profileSync.ts";

const cached = () => ({
  name_detection: { enabled: false, primary_name: "", aliases: [] },
  notification_preferences: { mode: "balanced", event_tiers: { bell: 2 } },
  display: { labels: false },
});
const receiver = () => ({
  name_detection: { enabled: true, primary_name: "Emma", aliases: ["Em"], learned_spellings: ["Ema"] },
  notification_preferences: { mode: "active", event_tiers: { bell: 3 } },
  display: { labels: true },
  revision: 8,
});

test("cold browser restore and receiver restart never turn cached preferences into edits", () => {
  const edits = new ProfileEdits();
  edits.observe(cached(), 0);
  assert.equal(edits.dirty, false);
  assert.deepEqual(edits.prepare(receiver()).profile, receiver());
  edits.observe(receiver(), 0);
  assert.equal(edits.dirty, false);
  assert.deepEqual(edits.prepare({ ...receiver(), revision: 9 }).profile, { ...receiver(), revision: 9 });
});

test("offline user edit merges only edited fields, preserving live name/settings", () => {
  const edits = new ProfileEdits();
  edits.observe(cached(), 0);
  edits.observe({ ...cached(), display: { labels: true } }, 1);
  assert.equal(edits.dirty, true);
  const saved = edits.prepare(receiver());
  assert.deepEqual(saved.profile.name_detection, receiver().name_detection);
  assert.deepEqual(saved.profile.notification_preferences, receiver().notification_preferences);
  assert.deepEqual(saved.profile.display, { labels: true });
  edits.acknowledge(saved.version);
  assert.equal(edits.dirty, false);
});

test("editing a name retains spellings installed by the name worker", () => {
  const edits = new ProfileEdits();
  edits.observe(cached(), 0);
  edits.observe({ ...cached(), name_detection: { enabled: true, primary_name: "Emma", aliases: ["Em"] } }, 1);
  assert.deepEqual(edits.prepare(receiver()).profile.name_detection, receiver().name_detection);
});

test("removing an override deletes it while preserving unrelated receiver overrides", () => {
  const edits = new ProfileEdits();
  edits.observe(cached(), 0);
  edits.observe({ ...cached(), notification_preferences: { mode: "balanced", event_tiers: {} } }, 1);
  const current = receiver();
  current.notification_preferences.event_tiers = { bell: 3, dog_bark: 2 } as typeof current.notification_preferences.event_tiers;
  assert.deepEqual(edits.prepare(current).profile.notification_preferences, {
    mode: "active", event_tiers: { dog_bark: 2 },
  });
});

test("an edit during an in-flight save remains pending after the older save completes", () => {
  const edits = new ProfileEdits();
  edits.observe(cached(), 0);
  edits.observe({ ...cached(), display: { labels: true } }, 1);
  const first = edits.prepare(receiver());
  edits.observe({ ...cached(), display: { labels: false } }, 2);
  edits.acknowledge(first.version);
  assert.equal(edits.dirty, true);
  const second = edits.prepare(first.profile);
  assert.deepEqual(second.profile.display, { labels: false });
  edits.acknowledge(second.version);
  assert.equal(edits.dirty, false);
});
