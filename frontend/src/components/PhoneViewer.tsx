import { useEffect, useState } from "react";
import Oled from "./Oled";
import {
  parseSnapshot,
  request,
  type ViewState,
  type SoundEvent,
  tierNames,
} from "../lib/events";

// Deliberately independent of useSession: viewers never sync a profile or send controls.
export default function PhoneViewer() {
  const [state, setState] = useState<ViewState | null>(null);
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController;
    async function poll() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2500);
      try {
        const next = parseSnapshot(
          await request("/state", undefined, controller.signal),
        );
        if (!stopped) {
          setState(next);
          setConnected(true);
        }
      } catch {
        if (!stopped) {
          setState(null);
          setConnected(false);
        }
      } finally {
        clearTimeout(timeout);
        if (!stopped) timer = setTimeout(poll, 250);
      }
    }
    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller?.abort();
    };
  }, []);
  const active = state?.active;
  const event =
    active ??
    (state?.confirm
      ? ({
          event_id: "resolved",
          type: "resolved",
          label: "Done",
          priority_tier: 1,
        } as unknown as SoundEvent)
      : null);
  return (
    <main className="phone-viewer">
      <header>
        <span>Aware</span>
        <span>Live mirror</span>
      </header>
      <p className="phone-status" role="status">
        {connected
          ? "Connected to the receiver"
          : "Connecting · keep the receiver running"}
      </p>
      <figure>
        <Oled
          event={event}
          labels={active ? (state?.display_labels ?? false) : false}
          direction={active ? state?.direction : state?.confirm?.direction}
        />
        <figcaption>Same 128×64 cue as the glasses</figcaption>
      </figure>
      <section aria-live="polite" aria-atomic="true">
        <h1>
          {!connected
            ? "Waiting for connection"
            : active
              ? active.label
              : state?.confirm
                ? "Acknowledged"
                : state?.paused
                  ? "Alerts paused"
                  : "All quiet"}
        </h1>
        <p>
          {active
            ? `${tierNames[active.priority_tier]} · ${active.source}${state?.direction ? ` · ${state.direction}` : ""}`
            : "Controls and sound settings stay on the companion laptop."}
        </p>
      </section>
      <footer>
        Read-only mirror · leave this page open
        <br />
        Phone lock or background tabs may pause updates.
      </footer>
    </main>
  );
}
