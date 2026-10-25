import test from "node:test";
import assert from "node:assert/strict";
import { parseSetupSuggestions } from "./setupSuggestions";
import {
  applySuggestedCues,
  applyCuratedRule,
  buildAwareProfile,
  AWARE_EMPTY_DRAFT,
} from "../../mana/AwareOnboarding.jsx";
const baby = {
  cue_id: "baby_cry",
  tier: 3 as const,
  reason: "Notice a baby calling for attention.",
};
test("Claude suggestions validate supported cues before review", () => {
  assert.deepEqual(
    parseSetupSuggestions({
      suggestions: [baby],
      provider: "Anthropic",
      model: "test",
    }).suggestions,
    [baby],
  );
  for (const row of [
    { ...baby, cue_id: "invented" },
    { ...baby, cue_id: "bicycle_bell" },
    { ...baby, cue_id: "name_called" },
    { ...baby, tier: 5 },
    { ...baby, reason: "" },
  ])
    assert.throws(() => parseSetupSuggestions({ suggestions: [row] }));
  assert.throws(() => parseSetupSuggestions({ suggestions: [baby, baby] }));
});
test("review application adds selected supported sounds without overriding existing Ignore", () => {
  const existing = applyCuratedRule(
    AWARE_EMPTY_DRAFT,
    "baby_cry",
    0,
    "my-baby",
  );
  const next = applySuggestedCues(existing, [
    baby,
    { cue_id: "rain", tier: 1, reason: "Quiet background awareness." },
  ]);
  const profile = buildAwareProfile(next);
  assert.equal(
    profile.custom_sound_requests?.find((r) => r.cue_id === "baby_cry")?.tier,
    0,
  );
  assert.equal(
    profile.custom_sound_requests?.find((r) => r.cue_id === "rain")?.tier,
    1,
  );
  assert.equal(buildAwareProfile(existing).custom_sound_requests?.length, 1);
});
test("applying no selections does nothing and builtin suggestions keep their canonical event route", () => {
  assert.deepEqual(
    buildAwareProfile(applySuggestedCues(AWARE_EMPTY_DRAFT, [])),
    buildAwareProfile(AWARE_EMPTY_DRAFT),
  );
  const profile = buildAwareProfile(
    applySuggestedCues(AWARE_EMPTY_DRAFT, [
      { cue_id: "fire_smoke", tier: 4, reason: "Urgent alarm." },
    ]),
  );
  assert.equal(profile.notification_preferences.event_tiers.smoke_alarm, 4);
  assert.deepEqual(profile.custom_sound_requests, []);
});

test('a fresh browser can render setup with no saved custom sound array', async()=>{
  const React=await import('react');
  const {renderToString}=await import('react-dom/server');
  const {default:Onboarding}=await import('../../mana/AwareOnboarding.jsx');
  const html=renderToString(React.createElement(Onboarding,{theme:'dark'}));
  assert.ok(html.includes('Choose your sounds'));
  assert.ok(html.includes('No sound recordings needed'));
  assert.ok(html.includes('Search sounds'));
});

test('first-use setup puts optional typed name before sound choices and has a clear finish action', async()=>{
  const React=await import('react');const {renderToString}=await import('react-dom/server');
  const {default:Onboarding}=await import('../../mana/AwareOnboarding.jsx');
  const html=renderToString(React.createElement(Onboarding,{theme:'dark',firstUse:true}));
  assert.ok(html.includes('Set up Aware'));
  assert.ok(html.indexOf('Your name (optional)')<html.indexOf('Search sounds'));
  assert.ok(html.includes('Nicknames'));
  assert.ok(html.includes('Start Aware'));
});

test('setup offers defaults and finish before optional catalog and Claude work', async()=>{
  const React=await import('react');const {renderToString}=await import('react-dom/server');
  const {default:Onboarding}=await import('../../mana/AwareOnboarding.jsx');
  const html=renderToString(React.createElement(Onboarding,{theme:'dark',firstUse:true}));
  assert.ok(html.indexOf('Your everyday alerts')<html.indexOf('Start Aware'));
  assert.ok(html.indexOf('Start Aware')<html.indexOf('Search sounds'));
  assert.ok(html.indexOf('Search sounds')<html.indexOf('Get sound suggestions from Claude'));
});

test('custom sound preview keeps the actual cue icon and Ignore without publishing anything', async()=>{
  const {makeSetupPreviewEvent}=await import('../../mana/AwareOnboarding.jsx');
  const event=makeSetupPreviewEvent({id:'baby_cry',event_type:'custom',label:'Baby crying',icon_id:'cue_baby_cry'},0);
  assert.equal(event.type,'custom');assert.equal(event.icon_id,'cue_baby_cry');
  assert.equal(event.label,'Baby crying');assert.equal(event.priority_tier,0);
  assert.equal(event.source,'mock');assert.equal(event.direction_degrees,null);
});

test('setup cannot finish while the receiver has unconfirmed preferences', async()=>{
  const React=await import('react');const {renderToString}=await import('react-dom/server');
  const {default:Onboarding}=await import('../../mana/AwareOnboarding.jsx');
  const html=renderToString(React.createElement(Onboarding,{theme:'dark',firstUse:true,canFinish:false}));
  assert.match(html,/<button[^>]*disabled=""[^>]*>Start Aware<\/button>/);
  assert.ok(html.includes('Waiting for your latest preferences to save'));
});
