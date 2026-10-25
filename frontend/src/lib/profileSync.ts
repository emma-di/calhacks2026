// Settings restored from browser storage are a cache, never an instruction to overwrite
// a running receiver. Only fields changed by a real user edit enter this patch.
type Fields = Record<string, unknown>;
const object = (value: unknown): value is Fields =>
  value !== null && typeof value === "object" && !Array.isArray(value);

export function changedFields(before: Fields, after: Fields): Fields {
  const patch: Fields = {};
  for (const key of new Set([...Object.keys(before), ...Object.keys(after)])) {
    const value = after[key];
    if (JSON.stringify(before[key]) === JSON.stringify(value)) continue;
    patch[key] = object(value) && object(before[key])
      ? changedFields(before[key], value)
      : value;
  }
  return patch;
}

export function mergeFields(base: Fields, patch: Fields): Fields {
  const next = { ...base };
  for (const [key, value] of Object.entries(patch)) {
    if (value === undefined) {
      delete next[key];
      continue;
    }
    next[key] = object(value) && object(next[key])
      ? mergeFields(next[key], value)
      : value;
  }
  return next;
}

function combinePatches(base: Fields, patch: Fields): Fields {
  const next = { ...base };
  for (const [key, value] of Object.entries(patch)) {
    next[key] = object(value) && object(next[key])
      ? combinePatches(next[key], value) : value;
  }
  return next;
}

export class ProfileEdits {
  private local: Fields | null = null;
  private editRevision = 0;
  private pending: Fields = {};
  private version = 0;

  observe(profile: Fields, editRevision: number) {
    if (this.local && editRevision !== this.editRevision) {
      this.pending = combinePatches(this.pending, changedFields(this.local, profile));
      this.version += 1;
    }
    this.local = profile;
    this.editRevision = editRevision;
  }

  get dirty() { return Object.keys(this.pending).length > 0; }
  prepare(remote: Fields) {
    return { version: this.version, profile: mergeFields(remote, this.pending), patch: this.pending };
  }
  acknowledge(version: number) {
    // An edit made while a save was in flight must still get its own save.
    if (version === this.version) this.pending = {};
  }
}


export type ProfileSyncStatus =
  | { kind: "local" }
  | { kind: "saving" }
  | { kind: "applied"; revision: number }
  | { kind: "error"; message: string };

export interface ProfileSyncCheckpoint {
  status: ProfileSyncStatus;
  editRevision: number;
  sessionId: string | null;
}

/** Render-time gate: a previous save never confirms a newer edit or receiver session.
 * This is deliberately independent of passive effects and network request timing.
 */
export function currentProfileSync(
  checkpoint: ProfileSyncCheckpoint,
  editRevision: number,
  sessionId: string | null,
  connected: boolean,
): ProfileSyncStatus {
  if (!connected) return { kind: "local" };
  if (checkpoint.editRevision !== editRevision || checkpoint.sessionId !== sessionId)
    return { kind: "saving" };
  return checkpoint.status;
}
