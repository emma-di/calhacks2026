// awareReceiverAdapter.js
// Profile read/write adapter for the Aware local receiver (same-origin /api proxy).
// Plain JavaScript ES module, no dependencies. Browser and Node 18+.
//
//   import { createAwareReceiverAdapter } from './awareReceiverAdapter.js';
//   const receiver = createAwareReceiverAdapter(request);
//   const profile = await receiver.readProfile(signal);
//   const saved = await receiver.saveEdits({ notification_preferences: { event_tiers: { dog_bark: 0 } } }, signal);
//   await receiver.saveEdits({ notification_preferences: { event_tiers: { dog_bark: undefined } } }); // reset to preset
//
// request(path, body?, signal?, method?) is supplied by the host app. It may resolve to the parsed JSON body,
// or to a fetch Response (checked with response.ok, then response.json()). Any rejection (offline receiver,
// proxy down, HTTP error, abort) is re-thrown unchanged: the adapter never reports a save it did not get back.
//
// Patch rules (saveEdits):
//   - plain objects merge recursively into a fresh GET /profile, so fields this edit did not touch keep their live values
//   - a key whose value is undefined is deleted (for example, removing an explicit tier returns it to the preset)
//   - arrays replace atomically (aliases, learned_spellings, custom_sound_requests)
//   - schema_version, profile_id and revision are server-owned and may not be patched
// Every save runs read -> merge -> validate -> PUT in one serialized queue; reads queue behind pending writes.

export class AwareReceiverError extends Error {
  constructor(message, details) {
    super(message);
    this.name = 'AwareReceiverError';
    if (details) Object.assign(this, details);
  }
}

export class AwareProfileValidationError extends AwareReceiverError {
  constructor(issues, stage) {
    super('Aware profile is invalid (' + stage + '): ' + issues.join('; '), { issues, stage });
    this.name = 'AwareProfileValidationError';
  }
}

const PROFILE_PATH = '/profile';
const SERVER_OWNED = ['schema_version', 'profile_id', 'revision'];
const FORBIDDEN_KEYS = new Set(['__proto__', 'constructor', 'prototype']);
const REQUEST_STATUSES = new Set(['pending', 'recognized']);

function isPlainObject(v) {
  if (v === null || typeof v !== 'object' || Array.isArray(v)) return false;
  const proto = Object.getPrototypeOf(v);
  return proto === Object.prototype || proto === null;
}

export function isAwareTier(v) {
  return Number.isInteger(v) && v >= 0 && v <= 4;
}

// Deep copy of JSON-like data. Drops undefined object values (they are not data).
function cloneData(v) {
  if (Array.isArray(v)) return v.map(cloneData);
  if (isPlainObject(v)) {
    const out = {};
    for (const k of Object.keys(v)) if (v[k] !== undefined) out[k] = cloneData(v[k]);
    return out;
  }
  return v;
}

// Deep copy of a patch that keeps undefined values, because they mean "delete this key".
function snapshotPatch(v, path) {
  if (Array.isArray(v)) return v.map((x, i) => snapshotPatch(x, path + '[' + i + ']'));
  if (isPlainObject(v)) {
    const out = {};
    for (const k of Object.keys(v)) {
      if (FORBIDDEN_KEYS.has(k)) throw new AwareReceiverError('Patch key not allowed: ' + path + k);
      out[k] = snapshotPatch(v[k], path + k + '.');
    }
    return out;
  }
  if (v === undefined || v === null || typeof v === 'string' || typeof v === 'boolean') return v;
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) throw new AwareReceiverError('Patch value at ' + path.replace(/\.$/, '') + ' is not a finite number.');
    return v;
  }
  throw new AwareReceiverError('Patch value at ' + path.replace(/\.$/, '') + ' is not JSON data.');
}

function mergeInto(target, patch) {
  for (const key of Object.keys(patch)) {
    const value = patch[key];
    if (value === undefined) delete target[key];
    else if (isPlainObject(value)) target[key] = mergeInto(isPlainObject(target[key]) ? target[key] : {}, value);
    else target[key] = cloneData(value); // arrays and primitives replace
  }
  return target;
}

// Pure merge: returns a new object; neither argument is modified.
export function mergeAwarePatch(base, patch) {
  if (!isPlainObject(patch)) throw new AwareReceiverError('Profile patch must be a plain object.');
  return mergeInto(isPlainObject(base) ? cloneData(base) : {}, snapshotPatch(patch, ''));
}

function checkTierMap(map, path, issues) {
  if (!isPlainObject(map)) { issues.push(path + ' must be an object'); return; }
  for (const k of Object.keys(map)) {
    if (!isAwareTier(map[k])) issues.push(path + '.' + k + ' must be an integer 0..4 (got ' + JSON.stringify(map[k]) + ')');
  }
}

// Returns a list of problems; an empty list means valid. Unknown fields are allowed and preserved.
export function validateAwareProfile(profile) {
  const issues = [];
  if (!isPlainObject(profile)) return ['profile must be an object'];
  if (profile.schema_version !== 1) issues.push('schema_version must be 1 (got ' + JSON.stringify(profile.schema_version) + ')');
  if (typeof profile.profile_id !== 'string' || profile.profile_id === '') issues.push('profile_id must be a non-empty string');
  if (!Number.isInteger(profile.revision) || profile.revision < 0) issues.push('revision must be a non-negative integer');

  const nd = profile.name_detection;
  if (!isPlainObject(nd)) issues.push('name_detection must be an object');
  else {
    if ('enabled' in nd && typeof nd.enabled !== 'boolean') issues.push('name_detection.enabled must be a boolean');
    if ('primary_name' in nd && typeof nd.primary_name !== 'string') issues.push('name_detection.primary_name must be a string');
    if ('language' in nd && typeof nd.language !== 'string') issues.push('name_detection.language must be a string');
    if ('aliases' in nd && !(Array.isArray(nd.aliases) && nd.aliases.every((a) => typeof a === 'string'))) issues.push('name_detection.aliases must be an array of strings');
  }

  const np = profile.notification_preferences;
  if (!isPlainObject(np)) issues.push('notification_preferences must be an object');
  else {
    if (typeof np.mode !== 'string' || np.mode === '') issues.push('notification_preferences.mode must be a non-empty string');
    checkTierMap(np.event_tiers, 'notification_preferences.event_tiers', issues);
    if ('category_tiers' in np) checkTierMap(np.category_tiers, 'notification_preferences.category_tiers', issues);
  }

  if ('custom_sound_requests' in profile) {
    const reqs = profile.custom_sound_requests;
    if (!Array.isArray(reqs)) issues.push('custom_sound_requests must be an array');
    else reqs.forEach((r, i) => {
      const p = 'custom_sound_requests[' + i + ']';
      if (!isPlainObject(r)) { issues.push(p + ' must be an object'); return; }
      if (typeof r.id !== 'string' || r.id === '') issues.push(p + '.id must be a non-empty string');
      if (typeof r.label !== 'string' || r.label === '') issues.push(p + '.label must be a non-empty string');
      if (!isAwareTier(r.tier)) issues.push(p + '.tier must be an integer 0..4 (got ' + JSON.stringify(r.tier) + ')');
      if (!REQUEST_STATUSES.has(r.status)) issues.push(p + '.status must be "pending" or "recognized"');
    });
  }

  if ('display' in profile) {
    if (!isPlainObject(profile.display)) issues.push('display must be an object');
    else if ('labels' in profile.display && typeof profile.display.labels !== 'boolean') issues.push('display.labels must be a boolean');
  }
  return issues;
}

function abortReason(signal) {
  if (signal.reason !== undefined) return signal.reason;
  return typeof DOMException === 'function' ? new DOMException('The operation was aborted.', 'AbortError') : new Error('Aborted');
}

function throwIfAborted(signal) {
  if (signal && signal.aborted) throw abortReason(signal);
}

function waitOrAbort(promise, signal) {
  if (!signal) return promise;
  if (signal.aborted) return Promise.reject(abortReason(signal));
  return new Promise((resolve, reject) => {
    const onAbort = () => reject(abortReason(signal));
    signal.addEventListener('abort', onAbort, { once: true });
    promise.then(
      (v) => { signal.removeEventListener('abort', onAbort); resolve(v); },
      (e) => { signal.removeEventListener('abort', onAbort); reject(e); },
    );
  });
}

export function createAwareReceiverAdapter(request) {
  if (typeof request !== 'function') throw new TypeError('createAwareReceiverAdapter(request): request must be a function');

  let tail = Promise.resolve();

  // Runs tasks one at a time, in call order. A task whose signal aborts while waiting leaves the queue without running.
  function enqueue(task, signal) {
    const previous = tail;
    let release;
    const done = new Promise((r) => { release = r; });
    tail = previous.then(() => done);
    return (async () => {
      try {
        await waitOrAbort(previous, signal);
        throwIfAborted(signal);
        return await task();
      } finally {
        release();
      }
    })();
  }

  async function call(method, body, signal) {
    throwIfAborted(signal);
    let result = await request(PROFILE_PATH, body, signal, method); // rejections propagate unchanged
    if (result && typeof result === 'object' && typeof result.json === 'function' && typeof result.ok === 'boolean') {
      if (!result.ok) {
        throw new AwareReceiverError(method + ' ' + PROFILE_PATH + ' failed with HTTP ' + result.status, { status: result.status, method });
      }
      result = await result.json();
    }
    if (result === undefined || result === null) {
      throw new AwareReceiverError(method + ' ' + PROFILE_PATH + ' returned no profile', { method });
    }
    return result;
  }

  async function fetchValidated(signal) {
    const live = await call('GET', undefined, signal);
    const issues = validateAwareProfile(live);
    if (issues.length) throw new AwareProfileValidationError(issues, 'read');
    return cloneData(live);
  }

  return {
    // GET /profile, validated. Queued behind any pending save, so it never returns a state older than a completed write.
    readProfile(signal) {
      return enqueue(() => fetchValidated(signal), signal);
    },

    // Apply only the user's edited fields on top of a fresh GET, validate, PUT, and resolve with the server's saved profile.
    saveEdits(patch, signal) {
      let snapshot;
      try {
        if (!isPlainObject(patch)) throw new AwareReceiverError('Profile patch must be a plain object.');
        for (const k of SERVER_OWNED) {
          if (Object.prototype.hasOwnProperty.call(patch, k)) throw new AwareReceiverError(k + ' is server-owned and cannot be patched.');
        }
        snapshot = snapshotPatch(patch, ''); // later caller mutations cannot change a queued edit
      } catch (e) {
        return Promise.reject(e);
      }

      return enqueue(async () => {
        const live = await fetchValidated(signal);
        const next = mergeInto(cloneData(live), snapshot);
        const issues = validateAwareProfile(next);
        if (issues.length) throw new AwareProfileValidationError(issues, 'before-write');
        throwIfAborted(signal);

        const saved = await call('PUT', next, signal);
        const savedIssues = validateAwareProfile(saved);
        if (savedIssues.length) throw new AwareProfileValidationError(savedIssues, 'write-response');
        if (!(saved.revision > live.revision)) {
          throw new AwareReceiverError('PUT ' + PROFILE_PATH + ' did not return a new revision (sent ' + live.revision + ', got ' + saved.revision + ')', { method: 'PUT' });
        }
        return cloneData(saved);
      }, signal);
    },
  };
}
