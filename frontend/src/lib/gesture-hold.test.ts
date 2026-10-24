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
