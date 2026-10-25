import { createAwareReceiverAdapter } from "../../mana/awareReceiverAdapter.js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { ProfileEdits } from "./profileSync";
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
  editRevision = 0,
) {
  const engine = useRef(new AlertEngine());
  const [view, setView] = useState<ViewState>(emptyView);
  const [connection, setConnection] = useState<Connection>("idle");
  const [sync, setSync] = useState<SyncStatus>({ kind: "local" });
  const [receiverProfile, setReceiverProfile] = useState<ManaProfile | null>(null);
  const edits = useRef(new ProfileEdits());
  const profileAdapter = useMemo(() => createAwareReceiverAdapter(request), []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const prefs: Preferences | null = profile
    ? ({ ...profile.notification_preferences,
        custom_sound_tiers: Object.fromEntries((profile.custom_sound_requests ?? []).map((sound) => [sound.id, sound.tier])),
      } as Preferences)
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

  // Hydrate from the receiver first. A stale localStorage draft must never PUT
  // automatically on connection or receiver restart. Only genuine user edits do.
  useEffect(() => {
    if (profile) edits.current.observe({ ...profile, display: { labels } }, editRevision);
  }, [profile, labels, editRevision]);

  const saves = useRef<Promise<unknown>>(Promise.resolve());
  useEffect(() => {
    if (source !== "receiver") {
      setReceiverProfile(null);
      setSync({ kind: "local" });
      return;
    }
    if (connection !== "connected") return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const reconcile = () => {
      saves.current = saves.current.catch(() => undefined).then(async () => {
        if (cancelled) return;
        try {
          // Read before each write: preserve fields changed by the audio/name
          // tools or another browser since this tab last hydrated.
          const remote = await profileAdapter.readProfile();
          if (cancelled) return;
          const pending = edits.current.prepare(remote as unknown as Record<string, unknown>);
          let applied = remote;
          if (edits.current.dirty) {
            setSync({ kind: "saving" });
            applied = await profileAdapter.saveEdits(pending.patch);
            edits.current.acknowledge(pending.version);
          }
          if (!cancelled) {
            // Never replace an edit that happened during the network request.
            if (!edits.current.dirty) setReceiverProfile((previous) =>
              JSON.stringify(previous) === JSON.stringify(applied) ? previous : applied);
            setSync({ kind: "applied", revision: applied.revision });
          }
        } catch (e) {
          if (!cancelled) setSync({ kind: "error", message: (e as Error).message });
        } finally {
          if (!cancelled) timer = setTimeout(reconcile, 2000);
        }
      });
    };
    reconcile();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [source, connection, view.session_id, editRevision, profileAdapter]);

  const send = useCallback(
    async (
      type: EventType,
      direction: Direction | number | null = null,
      provenance = "mock",
    ) => {
      const event = {
        ...makeMock(
          type,
          undefined,
          typeof direction === "number" ? direction : direction ? directionDegrees[direction] : null,
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
    async (type: EventType, direction: Direction | number | null = null) => {
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
    receiverProfile,
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
