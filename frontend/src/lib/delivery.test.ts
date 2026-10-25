import test from "node:test";
import assert from "node:assert/strict";
import { deliverEvent } from "./delivery.ts";
import { makeMock } from "./events.ts";

test("browser sound and camera gesture route locally without touching the receiver", async () => {
  const local: string[] = [];
  const post = async () => {
    throw new Error("Browser mode must not send HTTP");
  };
  for (const event of [
    makeMock("knock"),
    { ...makeMock("thumbs_up"), source: "camera" },
  ]) {
    await deliverEvent(
      "browser",
      event,
      (input) => local.push(input.type),
      post,
    );
  }
  assert.deepEqual(local, ["knock", "thumbs_up"]);
});

test("receiver route preserves provenance and never changes the browser engine", async () => {
  const event = { ...makeMock("thumbs_up"), source: "camera" };
  const calls: unknown[] = [];
  await deliverEvent(
    "receiver",
    event,
    () => {
      throw new Error("Must not run locally");
    },
    async (path, body) => {
      calls.push([path, body]);
    },
  );
  assert.deepEqual(calls, [["/events", { ...event, confidence: null }]]);
});
