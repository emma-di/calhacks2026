import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { Expand, Pause, Play, X } from "lucide-react";
import { SoundIcon } from "./components/Cue";
import Oled from "./components/Oled";
import Stage from "./components/Stage";
import { defaultAppearance, type Appearance } from "./lib/appearance";
import Onboarding, {
  type ManaProfile,
  type SetupChange,
} from "../mana/AwareOnboarding.jsx";
import {
  effectiveTier,
  type Direction,
  type FocusMode,
  type Preferences,
} from "./lib/alerts";
import { soundCatalog, sounds, tierNames, type SoundEvent } from "./lib/events";
import { explain, outcome } from "./lib/explain";
import { useSession, type Source, type SyncStatus } from "./lib/session";
import { useHearing } from "./lib/observations";
import HearingPanel from "./components/Hearing";

type View = "live" | "preferences" | "log";

const sourceLabel = (source: string) =>
  ({
    microphone: "Microphone",
    mock: "Test sound",
    replay: "Recording",
    simulation: "Simulation",
    camera: "Camera",
  })[source] ?? source;
const presetName = {
  balanced: "Balanced",
  gentle: "Gentle",
  active: "Active",
} as const;
const focusOptions: { key: FocusMode; label: string; detail: string }[] = [
  {
    key: "everyday",
    label: "Everyday",
    detail: "Everything you have not ignored comes through.",
  },
  {
    key: "work",
    label: "Work",
    detail: "Only Attention and Urgent come through.",
  },
  {
    key: "dnd",
    label: "Do not disturb",
    detail: "Only Urgent, like a smoke alarm, comes through.",
  },
];
const clock = (ms: number) =>
  new Date(ms).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
const lifetimeMs = { 0: 0, 1: 2000, 2: 3000, 3: 5000, 4: 30000 } as const;

// Segmented radio groups follow the same keyboard convention as native radios.
function radioKeys(event: ReactKeyboardEvent<HTMLDivElement>) {
  const keys = [
    "ArrowLeft",
    "ArrowRight",
    "ArrowUp",
    "ArrowDown",
    "Home",
    "End",
  ];
  if (!keys.includes(event.key)) return;
  const buttons = [
    ...event.currentTarget.querySelectorAll<HTMLButtonElement>(
      'button[role="radio"]:not(:disabled)',
    ),
  ];
  const index = buttons.indexOf(event.target as HTMLButtonElement);
  if (index < 0 || !buttons.length) return;
  event.preventDefault();
  const next =
    event.key === "Home"
      ? 0
      : event.key === "End"
        ? buttons.length - 1
        : (index +
            (["ArrowLeft", "ArrowUp"].includes(event.key) ? -1 : 1) +
            buttons.length) %
          buttons.length;
  buttons[next].focus();
  buttons[next].click();
}

function Mark() {
  // A lens with one lit cue in its corner: the product itself.
  return (
    <svg width="26" height="18" viewBox="0 0 26 18" aria-hidden="true">
      <rect
        x="1"
        y="1"
        width="24"
        height="16"
        rx="5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <rect x="14" y="9" width="7" height="4" fill="var(--signal)" />
    </svg>
  );
}

function syncText(source: Source, sync: SyncStatus, connected: boolean) {
  if (source === "browser") return "Saved in this browser.";
  if (!connected)
    return "Saved in this browser. Applies when the receiver connects.";
  if (sync.kind === "saving") return "Sending to the receiver…";
  if (sync.kind === "applied")
    return `Saved and applied to the receiver (version ${sync.revision}).`;
  if (sync.kind === "error")
    return `Saved here, but the receiver refused it: ${sync.message}`;
  return "Saved in this browser.";
}

export default function App() {
  const [view, setView] = useState<View>("live");
  const [audience, setAudience] = useState(false);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [view, audience]);
  const [source, setSource] = useState<Source>(() => {
    try {
      return localStorage.getItem("aware-source") === "receiver"
        ? "receiver"
        : "browser";
    } catch {
      return "browser";
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem("aware-source", source);
    } catch {
      // Storage can be unavailable (private windows); the choice then lasts for this visit.
    }
  }, [source]);
  const [profile, setProfile] = useState<ManaProfile | null>(null);
  const [appearance, setAppearance] = useState<Appearance>(defaultAppearance);
  const [labels, setLabels] = useState(false);
  const [testDirection, setTestDirection] = useState<Direction | null>(null);
  const [help, setHelp] = useState(false);
  const helpDialog = useRef<HTMLDialogElement>(null);
  const session = useSession(source, profile, labels);
  const { view: state, connection } = session;
  const connected = connection === "connected";
  const glasses = Boolean(
    source === "receiver" && connected && state.health?.display.connected,
  );
  const offline = source === "receiver" && !connected;
  const hearing = useHearing(source === "receiver" && connected);

  const applySetup = useCallback(
    ({ profile, display, direction }: SetupChange) => {
      setProfile(profile);
      setLabels(display.labels);
      setAppearance({
        text: display.labels ? "labels" : "icons",
        motion: display.motion === "pulse" ? "gentle" : "none",
        colors: { ...defaultAppearance.colors, ...display.colors },
        direction,
      });
    },
    [],
  );

  useEffect(() => {
    if (help) helpDialog.current?.showModal();
    else helpDialog.current?.close();
  }, [help]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAudience(false);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);

  const prefs = (profile?.notification_preferences ?? {
    mode: "balanced",
    event_tiers: {},
  }) as Preferences;
  const active = state.active;
  const direction = state.direction;
  const appliedLabels =
    source === "receiver" ? (state.display_labels ?? labels) : labels;
  const lensLabels = active ? appliedLabels : false; // The resolution check never has a label on hardware.

  // After the wearer resolves a cue, the lens and panel show a brief check where the cue was.
  const lensEvent: SoundEvent | null =
    active ??
    (state.confirm
      ? ({
          ...soundCatalog[0],
          event_id: "resolved",
          label: "Done",
          type: "resolved",
          priority_tier: 1,
        } as unknown as SoundEvent)
      : null);
  const lensDirection = active ? direction : (state.confirm?.direction ?? null);
  const latest = state.decisions.at(-1);
  const focus = focusOptions.find((f) => f.key === state.focus_mode)!;
  const sourceSummary =
    source === "browser"
      ? "Test sounds"
      : connected
        ? state.health?.capture.live
          ? "Recent audio events"
          : "Receiver ready"
        : connection === "connecting"
          ? "Connecting…"
          : "Receiver offline";
  const stageCaption = active
    ? `${sourceLabel(active.source)}${direction ? ` · from the ${direction}${active.source === "mock" ? " (simulated)" : ""}` : ""}`
    : source === "browser"
      ? "Through the lens"
      : sourceSummary;
  const narration = offline
    ? "The receiver is not answering. Start it with python3 -m audio.server."
    : latest
      ? explain(latest)
      : "Quiet. Tap a sound below and watch it reach the lens.";
  const waiting = state.queue
    .map((q) => sounds.find((s) => s.type === q.type)?.label ?? q.type)
    .join(", ");
  const fraction = active
    ? Math.max(
        0,
        Math.min(
          1,
          state.remaining_ms / (lifetimeMs[active.priority_tier] || 1),
        ),
      )
    : 0;

  const oledInset = (
    <figure className="oled-inset">
      <Oled event={lensEvent} labels={lensLabels} direction={lensDirection} />
      <figcaption>
        {glasses
          ? "Display client online · preview"
          : "Right-side display · 128×64"}
      </figcaption>
    </figure>
  );

  if (audience) {
    return (
      <div className="night audience">
        <Stage
          event={lensEvent}
          labels={lensLabels}
          direction={lensDirection}
          caption={stageCaption}
          motion={appearance.motion}
          onGesture={(eventId) => void session.dismiss(eventId)}
          accent={active ? appearance.colors[active.priority_tier] : undefined}
          large
        >
          {oledInset}
        </Stage>
        <div className="audience-bar">
          <p className="narration">{narration}</p>
          <button
            className="key"
            onClick={() => void session.dismiss()}
            disabled={!active}
          >
            Dismiss
          </button>
          <button className="key" onClick={() => setAudience(false)}>
            <X size={15} /> Exit
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="night">
      <header className="topbar">
        <a
          className="wordmark"
          href="#"
          onClick={(e) => (e.preventDefault(), setView("live"))}
        >
          <Mark /> aware
        </a>
        <nav className="tabs" aria-label="Main">
          {(
            [
              ["live", "Live"],
              ["preferences", "Preferences"],
              ["log", "Log"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              aria-current={view === key ? "page" : undefined}
              onClick={() => setView(key)}
            >
              {label}
              {key === "log" && state.events.length > 0 && (
                <span className="count">{state.events.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="top-status">
          <div
            className="switch"
            role="radiogroup"
            onKeyDown={radioKeys}
            aria-label="Sounds come from"
          >
            {(
              [
                ["browser", "Browser"],
                ["receiver", "Receiver"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                role="radio"
                aria-checked={source === key}
                tabIndex={source === key ? 0 : -1}
                onClick={() => setSource(key)}
              >
                {label}
              </button>
            ))}
          </div>
          <span
            className={`pill ${offline ? "is-off" : "is-on"}`}
            title={sourceSummary}
          >
            <span className="dot" />
            {sourceSummary}
          </span>
          <span className={`pill ${glasses ? "is-on" : "is-off"}`}>
            <span className="dot" />
            {glasses ? "Display client connected" : "Glasses not connected"}
          </span>
          <button
            className="pill pill-button"
            onClick={() => setAudience(true)}
          >
            <Expand size={13} /> Audience view
          </button>
          <button
            className="help-button"
            onClick={() => setHelp(true)}
            aria-label="How Aware works"
          >
            ?
          </button>
        </div>
      </header>

      <div className="mobile-session" role="status">
        <span>
          {sourceSummary} ·{" "}
          {glasses ? "Display client online" : "Glasses not connected"}
        </span>
        <button className="key" onClick={() => setAudience(true)}>
          <Expand size={14} /> Audience view
        </button>
      </div>

      {view === "live" && (
        <main className="live">
          <h1 className="sr-only">What the wearer sees</h1>
          <div className="lens-wrap">
            <Stage
              event={lensEvent}
              labels={lensLabels}
              direction={lensDirection}
              caption={stageCaption}
              motion={appearance.motion}
              onGesture={(eventId) => void session.dismiss(eventId)}
              accent={
                active ? appearance.colors[active.priority_tier] : undefined
              }
            />
            <div className="lifeline" aria-hidden="true">
              <div
                className={`lifeline-fill ${active?.priority_tier === 4 ? "is-urgent" : ""}`}
                style={{ transform: `scaleX(${fraction})` }}
              />
            </div>
          </div>
          <div className="narration-row">
            <div aria-live="polite">
              <p className="narration">{narration}</p>
              <p className="aside">
                {active
                  ? `${tierNames[active.priority_tier]} · ${Math.ceil(state.remaining_ms / 1000)} s left · ${direction ? `simulate looking ${direction}, or dismiss to resolve` : "dismiss to resolve"}${waiting ? ` · next: ${waiting}` : ""}`
                  : `${presetName[prefs.mode]} preset · ${focus.label}${state.paused ? " · paused" : ""}`}
              </p>
            </div>
            {oledInset}
          </div>

          <section className="dock" aria-label="Controls">
            <div className="keys" role="group" aria-label="Play a sound">
              {sounds.map((sound) => {
                const tier = effectiveTier(sound.type, sound.tier, prefs);
                return (
                  <button
                    key={sound.type}
                    className="key sound-key"
                    aria-current={
                      active?.type === sound.type ? "true" : undefined
                    }
                    disabled={
                      source === "receiver" && (!connected || !sound.receiver)
                    }
                    onClick={() => void session.play(sound.type, testDirection)}
                    title={
                      source === "receiver" && !sound.receiver
                        ? "The receiver has no detector for this sound"
                        : undefined
                    }
                  >
                    <SoundIcon type={sound.type} size={32} />
                    <span>{sound.label}</span>
                    <small className={`tier tier-${tier}`}>
                      {tierNames[tier]}
                    </small>
                  </button>
                );
              })}
            </div>
            <div className="dock-row">
              <div
                className="switch"
                role="radiogroup"
                onKeyDown={radioKeys}
                aria-label="Mode"
              >
                {focusOptions.map((option) => (
                  <button
                    key={option.key}
                    role="radio"
                    aria-checked={state.focus_mode === option.key}
                    tabIndex={state.focus_mode === option.key ? 0 : -1}
                    title={option.detail}
                    onClick={() =>
                      void session.setControls({ focus_mode: option.key })
                    }
                    disabled={offline}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <button
                className="key"
                aria-pressed={state.paused}
                onClick={() =>
                  void session.setControls({ paused: !state.paused })
                }
                disabled={offline}
              >
                {state.paused ? <Play size={14} /> : <Pause size={14} />}
                {state.paused ? "Resume" : "Pause"}
              </button>
              <span className="dock-spacer" />
              <button
                className="key"
                onClick={() => void session.dismiss()}
                disabled={!active}
              >
                Dismiss
              </button>
            </div>
            <details className="demo-tools">
              <summary>Test a direction or sequence</summary>
              <div className="dock-row">
                {" "}
                <div
                  className="switch"
                  role="radiogroup"
                  onKeyDown={radioKeys}
                  aria-label="Simulated direction of the next test sound"
                >
                  {([null, "left", "front", "right", "behind"] as const).map(
                    (d) => (
                      <button
                        key={d ?? "unknown"}
                        role="radio"
                        aria-checked={testDirection === d}
                        tabIndex={testDirection === d ? 0 : -1}
                        onClick={() => setTestDirection(d)}
                        title={
                          d
                            ? `Next test sound comes from the ${d} (simulated)`
                            : "No direction, as today's hardware reports"
                        }
                      >
                        {d ? d[0].toUpperCase() + d.slice(1) : "No direction"}
                      </button>
                    ),
                  )}
                </div>
                <button
                  className="key"
                  onClick={
                    session.busy ? session.stopSequence : session.playSequence
                  }
                  disabled={offline}
                >
                  {session.busy ? "Stop" : "Play a busy minute"}
                </button>
                {direction ? (
                  <button
                    className="key key-signal"
                    onClick={() => void session.look(direction)}
                  >
                    Simulate look {direction}
                  </button>
                ) : null}
              </div>
            </details>
            <p className="dock-note">
              {focus.detail}
              {state.paused ? " Paused hides every cue, urgent ones too." : ""}
              {session.error ? ` ${session.error}` : ""}
            </p>
          </section>
          {source === "receiver" && <HearingPanel hearing={hearing} />}
        </main>
      )}

      <div className="page preferences-view" hidden={view !== "preferences"}>
        <p className="sync-line" role="status">
          <span
            className={`dot ${source === "receiver" && session.sync.kind === "error" ? "is-off" : ""}`}
          />
          {syncText(source, session.sync, connected)}
        </p>
        <Onboarding
          theme="dark"
          onChange={applySetup}
          onComplete={() => setView("live")}
        />
      </div>

      {view === "log" && (
        <main className="page log-view">
          <h1>Log</h1>
          <p className="aside">
            {state.events.length}{" "}
            {state.events.length === 1 ? "sound" : "sounds"} this session ·{" "}
            {sourceSummary}
          </p>
          {state.decisions.length === 0 ? (
            <p className="empty">
              Nothing yet. Sounds you play or the receiver hears appear here.
            </p>
          ) : (
            <table className="log-table">
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Sound</th>
                  <th scope="col">From</th>
                  <th scope="col">Priority</th>
                  <th scope="col">Outcome</th>
                  <th scope="col">Why</th>
                </tr>
              </thead>
              <tbody>
                {[...state.decisions].reverse().map((d, i) => {
                  const event = state.events.find(
                    (e) => e.event_id === d.event_id,
                  );
                  return (
                    <tr key={`${d.event_id}-${d.reason}-${i}`}>
                      <td className="num">
                        {event ? clock(event.timestamp_ms) : "—"}
                      </td>
                      <td>
                        <span className="log-sound">
                          <SoundIcon
                            type={d.type as SoundEvent["type"]}
                            size={16}
                          />
                          {event?.label ??
                            soundCatalog.find((c) => c.type === d.type)
                              ?.label ??
                            d.type}
                        </span>
                      </td>
                      <td className="muted">
                        {event ? sourceLabel(event.source) : "—"}
                      </td>
                      <td>
                        <span className={`tier tier-${d.priority_tier}`}>
                          {tierNames[d.priority_tier]}
                        </span>
                      </td>
                      <td>{outcome(d.reason)}</td>
                      <td className="muted">{explain(d)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
          <details className="developer">
            <summary>Raw state for debugging</summary>
            <pre>{JSON.stringify(state, null, 2)}</pre>
          </details>
        </main>
      )}

      <dialog
        ref={helpDialog}
        onCancel={() => setHelp(false)}
        onClose={() => setHelp(false)}
        aria-labelledby="about-title"
        className="about"
      >
        <h2 id="about-title">How Aware works</h2>
        <ol className="about-flow">
          <li>
            <strong>Hear.</strong> A laptop model recognises a knock, a dog, a
            smoke alarm. Test sounds stand in here.
          </li>
          <li>
            <strong>Decide.</strong> One engine applies your priorities and
            mode, merges repeats, holds what can wait and remembers what you
            dismissed.
          </li>
          <li>
            <strong>Show.</strong> The glasses draw one small cue on a 128×64
            display. This page shows the same cue to everyone watching.
          </li>
        </ol>
        <dl className="ladder">
          {([4, 3, 2, 1] as const).map((tier) => (
            <div key={tier}>
              <dt className={`tier tier-${tier}`}>{tierNames[tier]}</dt>
              <dd>
                {tier === 4
                  ? "30 s, longer while it continues"
                  : `${lifetimeMs[tier] / 1000} s on screen`}
              </dd>
            </div>
          ))}
        </dl>
        <p className="aside">
          The glasses have no camera. Use POV camera adds an optional demo
          backdrop from this device; nothing is recorded. Aware can miss sounds
          or raise false alerts, so it is not a safety device.
        </p>
        <button
          className="key key-signal"
          autoFocus
          onClick={() => setHelp(false)}
        >
          Got it
        </button>
      </dialog>
    </div>
  );
}
