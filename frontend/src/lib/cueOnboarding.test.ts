import test from "node:test";
import assert from "node:assert/strict";
import {
  AWARE_EMPTY_DRAFT, applyCuratedRule, buildAwareProfile,
  createCueRule, sanitizeCustomSounds, searchCuratedSounds,
} from "../../mana/AwareOnboarding.jsx";
import catalog from "../../../audio/cue-catalog.json";

test("friendly Baby crying search and classifier-word aliases find its exact curated cue", () => {
  assert.equal(searchCuratedSounds("Baby crying")[0]?.id, "baby_cry");
  assert.equal(searchCuratedSounds("baby")[0]?.label, "Baby crying");
  assert.ok(searchCuratedSounds("smoke detector").some((cue) => cue.id === "fire_smoke"));
  assert.ok(searchCuratedSounds("  BABY  crying ").some((cue) => cue.id === "baby_cry"));
});

test("curated custom sound carries every model label, canonical icon and selected Ignore priority", () => {
  const cue = catalog.cues.find((item) => item.id === "doorbell")!;
  const draft = applyCuratedRule(AWARE_EMPTY_DRAFT, "doorbell", 0, "test-doorbell");
  const rule = buildAwareProfile(draft).custom_sound_requests?.[0];
  assert.equal(rule?.cue_id, "doorbell");
  assert.equal(rule?.status, "recognized");
  assert.equal(rule?.tier, 0);
  assert.equal(rule?.icon_id, cue.icon_id);
  assert.equal(rule?.icon, cue.icon_id);
  assert.deepEqual(rule?.model_labels, cue.model_labels);
  assert.equal(applyCuratedRule(draft, "doorbell", 2, "duplicate").custom_rules?.length, 1);
});

test("built-in fire alarm keeps its original event identity and auto-clear path", () => {
  const profile = buildAwareProfile(applyCuratedRule(AWARE_EMPTY_DRAFT, "fire_smoke", 4, "fire"));
  assert.equal(profile.notification_preferences.event_tiers.smoke_alarm, 4);
  assert.deepEqual(profile.custom_sound_requests, []);
  assert.equal(createCueRule("fire_smoke", 4, "fire"), null);
});

test("name and experimental bicycle options cannot silently enable an environmental detector", () => {
  for (const id of ["name_called", "bicycle_bell"]) {
    assert.equal(createCueRule(id, 3, id), null);
    assert.deepEqual(buildAwareProfile(applyCuratedRule(AWARE_EMPTY_DRAFT, id, 3, id)), buildAwareProfile(AWARE_EMPTY_DRAFT));
  }
  assert.equal(sanitizeCustomSounds([{id:"bike",label:"Bicycle bell",tier:2,status:"recognized",model_labels:["Bicycle bell"]}])[0]?.status, "pending");
});

test("all curated eligible rules survive export/hydration with their exact canonical mappings", () => {
  for (const cue of catalog.cues.filter((item) => item.event_type === "custom" && !item.experimental)) {
    const rule = createCueRule(cue.id, 2, `rule-${cue.id}`)!;
    assert.deepEqual(sanitizeCustomSounds([rule])[0], rule);
  }
});

test("custom rule capacity supports all curated choices plus niche pending requests", () => {
  const pending = Array.from({length:105}, (_, index) => ({id:String(index),label:`Niche sound ${index}`,tier:2,status:"pending"}));
  assert.equal(sanitizeCustomSounds(pending).length, 100);
});
