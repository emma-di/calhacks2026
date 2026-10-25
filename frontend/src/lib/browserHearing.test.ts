import test from "node:test";
import assert from "node:assert/strict";
import { detectSounds, directedQuestion, findCall, forDisplay, nameEvent, questionEvent } from "./browserHearing.ts";
import { parseEvent } from "./events.ts";

test("browser sound rules follow the YAMNet policy, cooldowns and picked sounds", () => {
  const last = new Map<string, number>();
  const picked = [{ id: "w", label: "my kettle", tier: 2, status: "recognized", model_labels: ["Whistle"], threshold: 0.2, icon: "cue_human_whistle" }];
  const events = detectSounds(new Map([["Knock", 0.6], ["Whistle", 0.5], ["Bicycle bell", 0.99]]), picked, last, 1000);
  assert.deepEqual(events.map((e) => e.type), ["knock", "custom"]);
  assert.equal(events[1].label, "my kettle");
  assert.equal(events[1].custom_sound_id, "w");
  events.forEach((e) => parseEvent(e));
  assert.equal(detectSounds(new Map([["Knock", 0.6]]), [], last, 3000).length, 0); // cooldown
  assert.equal(detectSounds(new Map([["Knock", 0.6]]), [], last, 7000).length, 1);
  assert.equal(detectSounds(new Map([["Knock", 0.05]]), [], new Map(), 0).length, 0);
});

test("speech finds your name first, then warnings, then attention calls", () => {
  assert.equal(findCall("Emma are you coming", ["Emma"])?.alias, "primary");
  assert.equal(findCall("hey watch out for the bike", ["Emma"])?.label, "Watch out!");
  assert.equal(findCall("excuse me do you have the time", ["Emma"])?.label, "Someone's calling");
  assert.equal(findCall("they went to the gemma store", ["Emma"]), null); // whole words only
});

test("questions match the receiver's rules and fit the display", () => {
  assert.equal(directedQuestion("Hey Emma are you coming to lunch with us later", ["Emma"]), "are you coming to lunch with us later?");
  assert.equal(directedQuestion("Emma, your package arrived.", ["Emma"]), null);
  assert.equal(forDisplay("um, what's the wifi password, Emma?"), "Whats the wifi password Emma?");
  const q = questionEvent("are you coming?", "Emma, are you coming?", 1);
  assert.equal(parseEvent(q).type, "question");
  assert.equal(parseEvent(nameEvent({ alias: "primary", label: "Your name", tier: 3 }, 1)).type, "name_called");
});
