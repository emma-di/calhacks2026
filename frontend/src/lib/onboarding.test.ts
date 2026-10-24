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
