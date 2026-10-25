import test from "node:test";
import assert from "node:assert/strict";
import { ProfileEdits, currentProfileSync, type ProfileSyncCheckpoint } from "./profileSync.ts";

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


function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

test("finish stays blocked from the edit render through pending GET and PUT, until that edit saves", async () => {
  const edits = new ProfileEdits();
  edits.observe(cached(), 0);
  let editRevision = 0;
  let checkpoint: ProfileSyncCheckpoint = {
    status: {kind:"applied", revision:8}, editRevision:0, sessionId:"receiver-a",
  };
  const canFinish = () => currentProfileSync(checkpoint, editRevision, "receiver-a", true).kind === "applied";
  assert.equal(canFinish(), true);

  // This is the render before passive effects or the initial read execute.
  editRevision = 1;
  assert.equal(canFinish(), false);
  edits.observe({...cached(), display:{labels:true}}, editRevision);
  checkpoint = {status:{kind:"saving"}, editRevision, sessionId:"receiver-a"};
  const read = deferred<ReturnType<typeof receiver>>();
  const write = deferred<ReturnType<typeof receiver>>();
  let writeStarted = false;
  const save = (async () => {
    const remote = await read.promise;
    const pending = edits.prepare(remote);
    writeStarted = true;
    const applied = await write.promise;
    edits.acknowledge(pending.version);
    checkpoint = {status:{kind:"applied",revision:applied.revision}, editRevision:1, sessionId:"receiver-a"};
  })();
  assert.equal(writeStarted, false);
  assert.equal(canFinish(), false);
  read.resolve(receiver());
  await Promise.resolve();
  assert.equal(writeStarted, true);
  assert.equal(canFinish(), false);
  write.resolve({...receiver(),revision:9});
  await save;
  assert.equal(edits.dirty,false);
  assert.equal(canFinish(),true);
});

test("stale successful saves or errors cannot confirm a newer edit, even before its effect runs", () => {
  const olderSuccess: ProfileSyncCheckpoint = {
    status:{kind:"applied",revision:9}, editRevision:1, sessionId:"receiver-a",
  };
  assert.deepEqual(currentProfileSync(olderSuccess,2,"receiver-a",true),{kind:"saving"});
  const olderError: ProfileSyncCheckpoint = {...olderSuccess,status:{kind:"error",message:"Old request failed"}};
  assert.deepEqual(currentProfileSync(olderError,2,"receiver-a",true),{kind:"saving"});
  const latestError: ProfileSyncCheckpoint = {...olderError,editRevision:2};
  assert.deepEqual(currentProfileSync(latestError,2,"receiver-a",true),latestError.status);
});

test("receiver restart and disconnection invalidate the previous finish confirmation", () => {
  const saved: ProfileSyncCheckpoint = {status:{kind:"applied",revision:8},editRevision:0,sessionId:"receiver-a"};
  assert.deepEqual(currentProfileSync(saved,0,"receiver-b",true),{kind:"saving"});
  assert.deepEqual(currentProfileSync(saved,0,"receiver-a",false),{kind:"local"});
  assert.equal(currentProfileSync({...saved,sessionId:"receiver-b"},0,"receiver-b",true).kind,"applied");
});
