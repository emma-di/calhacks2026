import test from "node:test";
import assert from "node:assert/strict";
import { levelFraction, parseObservation } from "./observations.ts";

const sample = {
  seq: 3, source: "microphone", model: "zipformer", inference_ms: 40, level_dbfs: -23.7,
  top: [{ label: "Dog", score: 0.73 }], rules: { dog_bark: { score: 0.49, threshold: 0.175, reason: "emitted" } },
  custom: [{ id: "kettle", label: "Kettle", score: 0.04, threshold: 0.7, reason: "below_threshold" }],
  emitted: [{ event_id: "e", type: "dog_bark", label: "Dog barking" }],
};

test("observations parse and reject malformed scores", () => {
  assert.equal(parseObservation(sample).top[0].label, "Dog");
  assert.throws(() => parseObservation({ ...sample, top: [{ label: "Dog", score: 1.5 }] }));
  assert.throws(() => parseObservation({ ...sample, seq: "3" }));
  assert.throws(() => parseObservation(null));
});

test("level meter maps dBFS onto 0..1", () => {
  assert.equal(levelFraction(0), 1);
  assert.equal(levelFraction(-30), 0.5);
  assert.equal(levelFraction(-100), 0);
});
