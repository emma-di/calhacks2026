import test from "node:test";
import assert from "node:assert/strict";
import {
  AWARE_EMPTY_DRAFT,
  buildAwareProfile,
  setAwareRule,
  removeAwareRule,
  resolveAwareTier,
} from "../../mana/AwareOnboarding.jsx";

test("Mana profile preserves Ignore through preset changes and removes reset exceptions", () => {
  const draft = setAwareRule(AWARE_EMPTY_DRAFT, "dog_bark", 0);
  const active = { ...draft, mode: "active" as const };
  assert.deepEqual(resolveAwareTier(active, "dog_bark"), {
    tier: 0,
    source: "rule",
  });
  assert.equal(
    buildAwareProfile(active).notification_preferences.event_tiers.dog_bark,
    0,
  );
  const reset = removeAwareRule(active, "dog_bark");
  assert.deepEqual(resolveAwareTier(reset, "dog_bark"), {
    tier: 2,
    source: "preset",
  });
  assert.deepEqual(
    buildAwareProfile(reset).notification_preferences.event_tiers,
    {},
  );
  assert.deepEqual(setAwareRule(active, "dog_bark", 9), active);
});


test("custom requests retain explicit Ignore without becoming detector event tiers", async () => {
  const { sanitizeCustomSounds } = await import("../../mana/AwareOnboarding.jsx");
  const custom = sanitizeCustomSounds([{id:"a",label:"  My kettle whistle  ",tier:0},
    {id:"b",label:"my kettle whistle",tier:4},{id:"c",label:" ",tier:2}]);
  assert.deepEqual(custom, [{id:"a",label:"My kettle whistle",tier:0,status:"pending"}]);
  const profile = buildAwareProfile({...AWARE_EMPTY_DRAFT, custom_rules:custom});
  assert.deepEqual(profile.custom_sound_requests, custom);
  assert.deepEqual(profile.notification_preferences.event_tiers, {});
});

test("model catalog selections preserve labels/icons and explicit Ignore", () => {
  const profile = buildAwareProfile({custom_rules:[{id:"whistle",label:"Whistling",tier:0,status:"recognized",model_labels:["Whistling"]}]});
  assert.equal(profile.custom_sound_requests?.[0].status,"recognized");
  assert.deepEqual(profile.custom_sound_requests?.[0].model_labels,["Whistling"]);
  assert.equal(profile.custom_sound_requests?.[0].tier,0);
});

test("hydrated named-disabled profile does not silently enable name recognition", () => {
  assert.equal(buildAwareProfile({name:"Emma",name_enabled:false}).name_detection.enabled,false);
});
