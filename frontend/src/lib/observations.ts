// Live "what the microphone hears" stream from GET /observations (audio/observations.py).
// One observation per analysis window (2 s of audio, every 1 s): top labels, every alert rule's
// decision, taught-sound scores and loudness. Raw audio never leaves the recognizer.
import { useEffect, useRef, useState } from "react";
import { request } from "./events";

export interface Observation {
  seq: number;
  source: string;
  model: string;
  inference_ms: number;
  level_dbfs: number;
  top: { label: string; score: number }[];
  rules: Record<string, { score: number; threshold: number; reason: string }>;
  custom: { id: string; label: string; score: number; threshold: number; reason: string }[];
  emitted: { event_id: string; type: string; label: string }[];
}

export interface Hearing {
  latest: Observation | null;
  // Local time (ms) the newest observation arrived; null before the first one.
  receivedAt: number | null;
  error: string | null;
}

const finite = (v: unknown, lo: number, hi: number) =>
  typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi;

export function parseObservation(input: unknown): Observation {
  const o = input as Record<string, unknown>;
  if (
    !o ||
    typeof o !== "object" ||
    !Number.isInteger(o.seq) ||
    typeof o.source !== "string" ||
    !finite(o.level_dbfs, -200, 10) ||
    !Array.isArray(o.top) ||
    !o.top.every((t) => t && typeof t.label === "string" && finite(t.score, 0, 1)) ||
    !Array.isArray(o.custom) ||
    !o.custom.every((c) => c && typeof c.label === "string" && finite(c.score, 0, 1)) ||
    !Array.isArray(o.emitted) ||
    typeof o.rules !== "object" ||
    o.rules === null
  )
    throw new Error("Invalid observation");
  return o as unknown as Observation;
}

/** Polls the receiver while `enabled`; resets when the receiver restarts. */
export function useHearing(enabled: boolean, intervalMs = 500): Hearing {
  const [state, setState] = useState<Hearing>({ latest: null, receivedAt: null, error: null });
  const since = useRef(0);
  const started = useRef<number | null>(null);
  useEffect(() => {
    if (!enabled) {
      since.current = 0;
      started.current = null;
      setState({ latest: null, receivedAt: null, error: null });
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const body = (await request(`/observations?since=${since.current}&limit=5`)) as {
          server_started_ms: number;
          observations: unknown[];
        };
        if (started.current !== body.server_started_ms) {
          started.current = body.server_started_ms;
          since.current = 0;
        }
        const newest = body.observations.at(-1);
        if (!cancelled && newest) {
          const latest = parseObservation(newest);
          since.current = latest.seq;
          setState({ latest, receivedAt: Date.now(), error: null });
        } else if (!cancelled) setState((s) => (s.error ? { ...s, error: null } : s));
      } catch (e) {
        if (!cancelled) setState((s) => ({ ...s, error: (e as Error).message }));
      } finally {
        if (!cancelled) timer = setTimeout(poll, intervalMs);
      }
    }
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [enabled, intervalMs]);
  return state;
}

/** 0..1 meter position for a dBFS level (-60 dB and below is empty). */
export const levelFraction = (dbfs: number) => Math.min(1, Math.max(0, (dbfs + 60) / 60));
