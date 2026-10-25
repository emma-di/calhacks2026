import test from "node:test";
import assert from "node:assert/strict";
import { GestureHold } from "./gesture-hold.ts";

test("a held thumbs-up fires once until released, even after cooldown", () => {
  const hold = new GestureHold();
  assert.equal(hold.update(true, 0), false);
  assert.equal(hold.update(true, 329), false);
  assert.equal(hold.update(true, 330), true);
  assert.equal(hold.update(true, 2500), false);
  assert.equal(hold.update(true, 9000), false);
  hold.update(false, 9010);
  assert.equal(hold.update(true, 9020), false);
  assert.equal(hold.update(true, 9350), true);
});

test("interrupted or brief gestures never dismiss and cooldown survives release", () => {
  const hold = new GestureHold();
  hold.update(true, 100);
  hold.update(false, 200);
  assert.equal(hold.update(true, 400), false);
  assert.equal(hold.update(true, 730), true);
  hold.update(false, 740);
  hold.update(true, 750);
  assert.equal(hold.update(true, 1080), false);
  assert.equal(hold.update(true, 2230), true);
});

test("camera hold is scoped to a cue and cannot spill onto a replacement", () => {
  const hold = new GestureHold(500, 1500, 250);
  hold.update(true, 0, "old");
  assert.equal(hold.update(true, 500, "new"), false);
  assert.equal(hold.update(true, 3000, "new"), false);
  hold.update(false, 3100, "new");
  hold.update(false, 3350, "new");
  assert.equal(hold.update(true, 3400, "new"), false);
  assert.equal(hold.update(true, 3900, "new"), true);
});

test("a hand held before an alert and a one-frame dropout cannot dismiss a new cue", () => {
  const hold = new GestureHold(500, 1500, 250);
  hold.update(true, 0, null);
  assert.equal(hold.update(true, 1000, "cue"), false);
  hold.update(false, 1100, "cue");
  assert.equal(hold.update(true, 1166, "cue"), false);
  assert.equal(hold.update(true, 2000, "cue"), false);
  hold.update(false, 2100, "cue");
  hold.update(false, 2350, "cue");
  hold.update(true, 2400, "cue");
  assert.equal(hold.update(true, 2900, "cue"), true);
});
