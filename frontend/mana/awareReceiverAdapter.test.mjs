// awareReceiverAdapter.test.mjs: contract test with a fake receiver. Run: node --test awareReceiverAdapter.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { createAwareReceiverAdapter, mergeAwarePatch, AwareProfileValidationError, AwareReceiverError } from './awareReceiverAdapter.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const baseProfile = () => ({
  schema_version: 1,
  profile_id: 'demo',
  revision: 7,
  name_detection: { enabled: true, primary_name: 'Em', aliases: ['Emmy'], language: 'en', sensitivity: 0.6 },
  notification_preferences: { mode: 'balanced', event_tiers: { dog_bark: 0, siren: 4 }, category_tiers: { alarms: 4 } },
  custom_sound_requests: [{ id: 'r1', label: 'Kettle whistle', tier: 2, status: 'pending' }],
  display: { labels: false },
  receiver_note: 'unknown top-level field',
});

// In-memory stand-in for the local backend: GET returns the stored profile; PUT checks the revision,
// stores the body and returns it with revision + 1. It records every call and any overlap between calls.
function fakeReceiver(initial, opts = {}) {
  let state = structuredClone(initial);
  const log = [];
  const puts = [];
  let active = 0;
  let overlapped = false;
  async function request(path, body, signal, method = 'GET') {
    active += 1;
    if (active > 1) overlapped = true;
    log.push(method + ' ' + path);
    try {
      await sleep(opts.delayMs ?? 5);
      if (signal && signal.aborted) throw signal.reason;
      if (opts.failGet && method === 'GET') throw opts.failGet();
      if (path !== '/profile') throw new Error('404 ' + path);
      if (method === 'GET') return structuredClone(state);
      if (method === 'PUT') {
        puts.push(structuredClone(body));
        const putError = opts.failPut ? opts.failPut() : null;
        if (putError) throw putError;
        if (body.revision !== state.revision) { const e = new Error('409 stale revision'); e.status = 409; throw e; }
        state = { ...structuredClone(body), revision: opts.keepRevision ? state.revision : state.revision + 1 };
        return structuredClone(state);
      }
      throw new Error('405 ' + method);
    } finally {
      active -= 1;
    }
  }
  return { request, log, puts, get state() { return state; }, set state(v) { state = v; }, get overlapped() { return overlapped; } };
}

test('Ignore (0) survives a write in both directions', async () => {
  const rx = fakeReceiver({ ...baseProfile(), notification_preferences: { mode: 'balanced', event_tiers: {} } });
  const adapter = createAwareReceiverAdapter(rx.request);
  const saved = await adapter.saveEdits({ notification_preferences: { event_tiers: { dog_bark: 0 } } });
  assert.equal(rx.puts[0].notification_preferences.event_tiers.dog_bark, 0);
  assert.equal(saved.notification_preferences.event_tiers.dog_bark, 0);
  assert.ok(Object.hasOwn(saved.notification_preferences.event_tiers, 'dog_bark'));
  assert.equal(JSON.stringify(rx.puts[0].notification_preferences.event_tiers), '{"dog_bark":0}');
  // An existing 0 is untouched by an unrelated edit.
  const again = await adapter.saveEdits({ notification_preferences: { event_tiers: { knock: 2 } } });
  assert.deepEqual(again.notification_preferences.event_tiers, { dog_bark: 0, knock: 2 });
});

test('an unrelated tier edit does not overwrite the live name, learned spellings or unknown fields', async () => {
  const rx = fakeReceiver(baseProfile());
  const adapter = createAwareReceiverAdapter(rx.request);
  const seenByUi = await adapter.readProfile();
  assert.equal(seenByUi.name_detection.primary_name, 'Em');

  // Meanwhile another writer (the name worker or another tab) updates the name fields on the receiver.
  rx.state = structuredClone(rx.state);
  rx.state.name_detection.primary_name = 'Emma';
  rx.state.name_detection.learned_spellings = ['Emah', 'Ema'];
  rx.state.revision += 1; // 8

  const saved = await adapter.saveEdits({ notification_preferences: { event_tiers: { knock: 3 } } });
  const sent = rx.puts[0];
  assert.equal(sent.revision, 8, 'PUT is based on the fresh GET, not the UI copy');
  assert.equal(sent.name_detection.primary_name, 'Emma');
  assert.deepEqual(sent.name_detection.learned_spellings, ['Emah', 'Ema']);
  assert.equal(sent.name_detection.sensitivity, 0.6);
  assert.equal(sent.receiver_note, 'unknown top-level field');
  assert.deepEqual(sent.custom_sound_requests, baseProfile().custom_sound_requests);
  assert.deepEqual(sent.notification_preferences.category_tiers, { alarms: 4 });
  assert.deepEqual(sent.notification_preferences.event_tiers, { dog_bark: 0, siren: 4, knock: 3 });
  assert.equal(saved.revision, 9);
  assert.equal(saved.name_detection.primary_name, 'Emma');
});

test('a failed PUT rejects with the original error and the queue keeps working', async () => {
  const offline = new Error('connect ECONNREFUSED 127.0.0.1:8765');
  let fail = true;
  const rx = fakeReceiver(baseProfile(), { failPut: () => (fail ? offline : null) });
  const adapter = createAwareReceiverAdapter(rx.request);
  await assert.rejects(adapter.saveEdits({ notification_preferences: { mode: 'gentle' } }), (e) => e === offline);
  assert.equal(rx.state.notification_preferences.mode, 'balanced');
  assert.equal(rx.state.revision, 7);
  fail = false;
  const saved = await adapter.saveEdits({ notification_preferences: { mode: 'gentle' } });
  assert.equal(saved.notification_preferences.mode, 'gentle');
  assert.equal(saved.revision, 8);
});

test('a failed GET rejects and no PUT is attempted', async () => {
  const down = new TypeError('Failed to fetch');
  const rx = fakeReceiver(baseProfile(), { failGet: () => down });
  const adapter = createAwareReceiverAdapter(rx.request);
  await assert.rejects(adapter.readProfile(), (e) => e === down);
  await assert.rejects(adapter.saveEdits({ display: { labels: true } }), (e) => e === down);
  assert.equal(rx.puts.length, 0);
});

test('concurrent saves serialize as GET, PUT, GET, PUT and both edits land', async () => {
  const rx = fakeReceiver(baseProfile(), { delayMs: 15 });
  const adapter = createAwareReceiverAdapter(rx.request);
  const [a, b, r] = await Promise.all([
    adapter.saveEdits({ notification_preferences: { event_tiers: { knock: 1 } } }),
    adapter.saveEdits({ notification_preferences: { event_tiers: { bell: 3 } } }),
    adapter.readProfile(),
  ]);
  assert.deepEqual(rx.log, ['GET /profile', 'PUT /profile', 'GET /profile', 'PUT /profile', 'GET /profile']);
  assert.equal(rx.overlapped, false, 'no two receiver calls were in flight at once');
  assert.equal(a.revision, 8);
  assert.equal(b.revision, 9);
  assert.deepEqual(b.notification_preferences.event_tiers, { dog_bark: 0, siren: 4, knock: 1, bell: 3 });
  assert.equal(r.revision, 9, 'a read queued after writes sees them');
});

test('undefined deletes a key (back to preset); arrays replace atomically', async () => {
  const rx = fakeReceiver(baseProfile());
  const adapter = createAwareReceiverAdapter(rx.request);
  const saved = await adapter.saveEdits({
    notification_preferences: { event_tiers: { siren: undefined } },
    name_detection: { aliases: ['Emmy', 'Em D'] },
  });
  assert.deepEqual(saved.notification_preferences.event_tiers, { dog_bark: 0 });
  assert.ok(!Object.hasOwn(rx.puts[0].notification_preferences.event_tiers, 'siren'));
  assert.deepEqual(saved.name_detection.aliases, ['Emmy', 'Em D']);
  assert.deepEqual(mergeAwarePatch({ list: [1, 2, 3] }, { list: [9] }), { list: [9] });
});

test('invalid tiers and schema versions are refused before any PUT', async () => {
  for (const bad of [5, -1, 2.5, '2', null, NaN]) {
    const rx = fakeReceiver(baseProfile());
    const adapter = createAwareReceiverAdapter(rx.request);
    await assert.rejects(adapter.saveEdits({ notification_preferences: { event_tiers: { knock: bad } } }),
      (e) => e instanceof AwareProfileValidationError || e instanceof AwareReceiverError);
    assert.equal(rx.puts.length, 0, 'no PUT for tier ' + String(bad));
  }
  const rxReq = fakeReceiver(baseProfile());
  await assert.rejects(createAwareReceiverAdapter(rxReq.request).saveEdits({ custom_sound_requests: [{ id: 'r2', label: 'Microwave', tier: 7, status: 'pending' }] }), AwareProfileValidationError);
  await assert.rejects(createAwareReceiverAdapter(rxReq.request).saveEdits({ notification_preferences: { category_tiers: { alarms: '4' } } }), AwareProfileValidationError);
  assert.equal(rxReq.puts.length, 0);

  const rxV2 = fakeReceiver({ ...baseProfile(), schema_version: 2 });
  await assert.rejects(createAwareReceiverAdapter(rxV2.request).saveEdits({ display: { labels: true } }), (e) => e instanceof AwareProfileValidationError && e.stage === 'read');
  assert.equal(rxV2.puts.length, 0);

  const rxOwned = fakeReceiver(baseProfile());
  await assert.rejects(createAwareReceiverAdapter(rxOwned.request).saveEdits({ revision: 99 }), AwareReceiverError);
  await assert.rejects(createAwareReceiverAdapter(rxOwned.request).saveEdits({ schema_version: 1 }), AwareReceiverError);
  assert.equal(rxOwned.log.length, 0);
});

test('a PUT that does not return a new revision is not reported as saved', async () => {
  const rx = fakeReceiver(baseProfile(), { keepRevision: true });
  await assert.rejects(createAwareReceiverAdapter(rx.request).saveEdits({ display: { labels: true } }), /did not return a new revision/);
});

test('fetch Response results are checked for ok', async () => {
  const request = async () => ({ ok: false, status: 503, json: async () => ({}) });
  await assert.rejects(createAwareReceiverAdapter(request).readProfile(), (e) => e instanceof AwareReceiverError && e.status === 503);
});

test('an aborted save never sends a PUT', async () => {
  const rx = fakeReceiver(baseProfile(), { delayMs: 20 });
  const adapter = createAwareReceiverAdapter(rx.request);
  const ctl = new AbortController();
  const p = adapter.saveEdits({ display: { labels: true } }, ctl.signal);
  setTimeout(() => ctl.abort(), 5);
  await assert.rejects(p, (e) => e.name === 'AbortError');
  assert.equal(rx.puts.length, 0);
  const ok = await adapter.saveEdits({ display: { labels: true } });
  assert.equal(ok.display.labels, true);
});
