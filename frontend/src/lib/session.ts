import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertEngine,
  directionDegrees,
  type Direction,
  type FocusMode,
  type Preferences,
} from "./alerts";
import {
  makeMock,
  parseSnapshot,
  request,
  type EventType,
  type ViewState,
} from "./events";
import { deliverEvent } from "./delivery";
import type { ManaProfile } from "../../mana/AwareOnboarding.jsx";

export type Source = "browser" | "receiver";
export type Connection = "idle" | "connecting" | "connected" | "disconnected";
export type SyncStatus =
  | { kind: "local" }
  | { kind: "saving" }
  | { kind: "applied"; revision: number }
  | { kind: "error"; message: string };

const emptyView = (): ViewState => ({
  display_labels: null,
  active: null,
  events: [],
  decisions: [],
  remaining_ms: 0,
  direction: null,
  confirm: null,
  state_sequence: 0,
  focus_mode: "everyday",
  paused: false,
  queue: [],
  health: null,
  session_id: null,
  observations: [],
});

// Knock is skipped for nothing, name takes over, the alarm takes over and repeats; dismiss to see
// the name come back. Each step is narrated by the decision explanations.
const busyMinute: [number, EventType][] = [
  [0, "knock"],
  [900, "dog_bark"],
  [1800, "name_called"],
  [3600, "smoke_alarm"],
  [5600, "smoke_alarm"],
];

export function useSession(
  source: Source,
  profile: ManaProfile | null,
  labels: boolean,
) {
  const engine = useRef(new AlertEngine());
  const [view, setView] = useState<ViewState>(emptyView);
  const [connection, setConnection] = useState<Connection>("idle");
  const [sync, setSync] = useState<SyncStatus>({ kind: "local" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const prefs: Preferences | null = profile
    ? (profile.notification_preferences as Preferences)
    : null;

  const stopSequence = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setBusy(false);
  }, []);

  // Browser simulator: same engine rules, local clock.
  useEffect(() => {
    if (prefs) engine.current.prefs = prefs;
  }, [prefs]);
  useEffect(() => {
    if (source !== "browser") return;
    const tick = () =>
      setView({
        ...emptyView(),
        ...engine.current.snapshot(performance.now()),
      });
    tick();
    const timer = setInterval(tick, 100);
    return () => clearInterval(timer);
  }, [source]);

  // Receiver: poll the authoritative state; never keep a cue from a dead connection.
  useEffect(() => {
    if (source !== "receiver") return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController | undefined;
    setConnection("connecting");
    setView(emptyView());
    async function poll() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller?.abort(), 2500);
      try {
        const snapshot = parseSnapshot(
          await request("/state", undefined, controller.signal),
        );
        if (!cancelled) {
          setView(snapshot);
          setConnection("connected");
        }
      } catch {
        if (!cancelled) {
          setConnection("disconnected");
          setView((v) => ({
            ...v,
            active: null,
            confirm: null,
            remaining_ms: 0,
            health: null,
          }));
        }
      } finally {
        clearTimeout(timeout);
        if (!cancelled) timer = setTimeout(poll, 250);
      }
    }
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
      controller?.abort();
    };
  }, [parseSnapshot, source]);

  // Saved preferences follow the receiver, including after it restarts with a new session.
  const synced = useRef<string | null>(null);
  const saves = useRef<Promise<unknown>>(Promise.resolve());
  const profileKey = profile
    ? JSON.stringify([
        profile.notification_preferences,
        profile.custom_sound_requests,
        profile.name_detection,
        labels,
      ])
    : null;
  useEffect(() => {
    if (source !== "receiver") {
      synced.current = null;
      setSync({ kind: "local" });
      return;
    }
    if (connection !== "connected" || !profile || !profileKey) return;
    const key = `${view.session_id}:${profileKey}`;
    if (synced.current === key) return;
    synced.current = key;
    setSync({ kind: "saving" });
    let cancelled = false;
    // Preserve edit order: an older, slower request must not overwrite the latest settings.
    saves.current = saves.current
      .catch(() => undefined)
      .then(async () => {
        if (cancelled) return;
        try {
          const saved = await request(
            "/profile",
            { ...profile, display: { labels } },
            undefined,
            "PUT",
          );
          if (!cancelled)
            setSync({
              kind: "applied",
              revision: Number((saved as { revision: number }).revision),
            });
        } catch (e) {
          if (synced.current === key) synced.current = null;
          if (!cancelled)
            setSync({ kind: "error", message: (e as Error).message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [source, connection, profile, profileKey, labels, view.session_id]);

  const send = useCallback(
    async (
      type: EventType,
      direction: Direction | null = null,
      provenance = "mock",
    ) => {
      const event = {
        ...makeMock(
          type,
          undefined,
          direction ? directionDegrees[direction] : null,
        ),
        source: provenance,
      };
      await deliverEvent(
        source,
        event,
        (input) => engine.current.add(input, performance.now()),
        request,
      );
    },
    [source],
  );

  const play = useCallback(
    async (type: EventType, direction: Direction | null = null) => {
      stopSequence();
      setError(null);
      if (source === "browser") engine.current.reset(performance.now());
      try {
        await send(type, direction);
      } catch {
        setError(
          "The receiver did not accept that sound. Check that it is running.",
        );
      }
    },
    [source, send, stopSequence],
  );

  const playSequence = useCallback(() => {
    stopSequence();
    setError(null);
    if (source === "browser") engine.current.reset(performance.now());
    setBusy(true);
    timers.current = busyMinute.map(([delay, type]) =>
      setTimeout(
        () =>
          void send(type).catch(() =>
            setError("The receiver stopped answering."),
          ),
        delay,
      ),
    );
    timers.current.push(
      setTimeout(() => setBusy(false), busyMinute.at(-1)![0] + 100),
    );
  }, [source, send, stopSequence]);

  const dismiss = useCallback(
    async (expectedEventId?: string) => {
      const id = expectedEventId ?? view.active?.event_id;
      if (!id) return;
      if (source === "browser") {
        engine.current.dismiss(performance.now(), id);
        return;
      }
      try {
        await request("/dismiss", { event_id: id });
      } catch {
        setError("Dismiss did not reach the receiver.");
      }
    },
    [source, view.active],
  );

  // A dismiss gesture from the camera, or the dock button standing in for it.
  const gesture = useCallback(
    async (source: "camera" | "mock" = "mock") => {
      try {
        await send("thumbs_up", null, source);
      } catch {
        setError("The gesture did not reach the receiver.");
      }
    },
    [send],
  );

  const look = useCallback(
    async (direction: Direction) => {
      if (source === "browser") {
        engine.current.look(performance.now(), direction);
        return;
      }
      try {
        await request("/look", { direction });
      } catch {
        setError("The look did not reach the receiver.");
      }
    },
    [source],
  );

  const setControls = useCallback(
    async (changes: { focus_mode?: FocusMode; paused?: boolean; repeat_suppression?: boolean; snap_to_dismiss?: boolean }) => {
      if (source === "browser") {
        engine.current.setControls(performance.now(), changes);
        return;
      }
      try {
        await request("/controls", changes);
      } catch {
        setError("That change did not reach the receiver.");
      }
    },
    [source],
  );

  useEffect(() => stopSequence, [source, stopSequence]);

  return {
    view,
    connection,
    sync,
    busy,
    error,
    play,
    playSequence,
    stopSequence,
    dismiss,
    look,
    gesture,
    setControls,
  };
}
