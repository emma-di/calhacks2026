import { useEffect, useState } from "react";

export interface PiChannelLevel {
  channel: 0 | 1;
  rms_dbfs: number;
  peak_dbfs: number;
  clip_fraction: number;
}
export interface PiLevelsSnapshot {
  schema_version: 1;
  sample_rate: 48000;
  channels: 2;
  sequence: number;
  age_ms: number | null;
  connected: boolean;
  levels: PiChannelLevel[];
  error: string | null;
}
export interface PiLevelsState {
  snapshot: PiLevelsSnapshot | null;
  receivedAt: number | null;
  advancedAt: number | null;
  error: string | null;
}
export const PI_LEVEL_STALE_MS = 1500;
export const emptyPiLevels = (): PiLevelsState => ({
  snapshot: null, receivedAt: null, advancedAt: null, error: null,
});
const finite = (value: unknown, min: number, max = Number.MAX_SAFE_INTEGER) =>
  typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;

export function parsePiLevels(input: unknown): PiLevelsSnapshot {
  if (!input || typeof input !== "object") throw new Error("Invalid Pi audio levels");
  const value = input as Record<string, unknown>;
  if (value.schema_version !== 1 || value.sample_rate !== 48000 || value.channels !== 2 ||
      !Number.isSafeInteger(value.sequence) || !finite(value.sequence, 0) ||
      typeof value.connected !== "boolean" ||
      !(value.age_ms === null || finite(value.age_ms, 0)) ||
      !(value.error === null || (typeof value.error === "string" && value.error.length <= 2000)) ||
      !Array.isArray(value.levels) ||
      !(value.levels.length === 2 || (!value.connected && value.levels.length === 0)) ||
      (value.connected && value.age_ms === null) ||
      !value.levels.every((channel, index) => channel && typeof channel === "object" && channel.channel === index &&
        finite(channel.rms_dbfs, -200, 0) && finite(channel.peak_dbfs, -200, 0) &&
        finite(channel.clip_fraction, 0, 1))) {
    throw new Error("Invalid Pi audio levels");
  }
  return value as unknown as PiLevelsSnapshot;
}

export function receivePiLevels(previous: PiLevelsState, snapshot: PiLevelsSnapshot, now: number): PiLevelsState {
  const advanced = !previous.snapshot || previous.snapshot.sequence !== snapshot.sequence;
  return { snapshot, receivedAt: now, advancedAt: advanced ? now : previous.advancedAt, error: null };
}
export function failPiLevels(message: string): PiLevelsState {
  return { ...emptyPiLevels(), error: message };
}

/** A quiet channel is connected; only transport, age and sample progress decide freshness. */
export function displayPiLevels(state: PiLevelsState, now: number): {
  status: "pending" | "offline" | "stale" | "live";
  levels: PiChannelLevel[] | null;
} {
  const value = state.snapshot;
  if (!value) return { status: state.error ? "offline" : "pending", levels: null };
  if (!value.connected) return { status: "offline", levels: null };
  const age = (value.age_ms ?? Infinity) + Math.max(0, now - (state.receivedAt ?? now));
  const withoutProgress = Math.max(0, now - (state.advancedAt ?? now));
  if (age >= PI_LEVEL_STALE_MS || withoutProgress >= PI_LEVEL_STALE_MS)
    return { status: "stale", levels: null };
  return { status: "live", levels: value.levels };
}

export const piLevelFraction = (dbfs: number) => Math.max(0, Math.min(1, (dbfs + 60) / 60));

/** Separate Pi bridge: this does not change the recognizer's input or saved preferences. */
export function usePiMicrophoneLevels(enabled = true) {
  const [state, setState] = useState<PiLevelsState>(emptyPiLevels);
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    if (!enabled) {
      setState(emptyPiLevels());
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController | undefined;
    const clock = setInterval(() => setNow(Date.now()), 200);
    async function poll() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller?.abort(), 2000);
      try {
        const response = await fetch("/pi-audio/levels", { signal: controller.signal, cache: "no-store" });
        if (!response.ok) throw new Error("Pi audio bridge is not available.");
        const value = parsePiLevels(await response.json());
        if (!cancelled) setState((previous) => receivePiLevels(previous, value, Date.now()));
      } catch (error) {
        if (!cancelled) setState(failPiLevels(error instanceof Error && error.name !== "AbortError"
          ? error.message : "Pi audio bridge did not answer."));
      } finally {
        clearTimeout(timeout);
        if (!cancelled) timer = setTimeout(poll, 200);
      }
    }
    void poll();
    return () => {
      cancelled = true;
      clearInterval(clock);
      clearTimeout(timer);
      controller?.abort();
    };
  }, [enabled]);
  return { ...displayPiLevels(state, now), error: state.error ?? state.snapshot?.error ?? null };
}
