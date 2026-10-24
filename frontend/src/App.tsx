import { useCallback, useEffect, useRef, useState } from "react";
import { Expand, Menu, Pause, Play, X } from "lucide-react";
import { SoundIcon } from "./components/Cue";
import Oled from "./components/Oled";
import Stage from "./components/Stage";
import { defaultAppearance, type Appearance } from "./lib/appearance";
import Onboarding, {
  type ManaProfile,
  type SetupChange,
} from "../mana/AwareOnboarding.jsx";
import { effectiveTier, type FocusMode, type Preferences } from "./lib/alerts";
import { sounds, tierNames, type SoundEvent } from "./lib/events";
import { explain, outcome } from "./lib/explain";
import { useSession, type Source, type SyncStatus } from "./lib/session";

type View = "live" | "preferences" | "log";

const sourceLabel = (source: string) =>
  ({ microphone: "Microphone", mock: "Test sound", replay: "Recording", simulation: "Simulation" })[
    source
  ] ?? source;
const presetName = { balanced: "Balanced", gentle: "Gentle", active: "Active" } as const;
const focusOptions: { key: FocusMode; label: string; detail: string }[] = [
  { key: "everyday", label: "Everyday", detail: "Every sound you have not ignored comes through." },
  { key: "work", label: "Work", detail: "Only Attention and Urgent sounds come through." },
  { key: "dnd", label: "Do not disturb", detail: "Only Urgent sounds, like a smoke alarm, come through." },
];
const clock = (ms: number) =>
  new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const lifetimeMs = { 0: 0, 1: 2000, 2: 3000, 3: 5000, 4: 30000 } as const;

function Mark() {
  // A lens with one lit cue in its lower corner: the product, not a letter in a square.
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
      <rect x="2" y="6" width="24" height="16" rx="4" fill="#141414" />
      <rect x="15" y="14" width="7" height="4" rx="1" fill="#fff" />
    </svg>
  );
}

function syncText(source: Source, sync: SyncStatus, connected: boolean) {
  if (source === "browser") return "Saved in this browser";
  if (!connected) return "Saved in this browser. Applies when the receiver connects.";
  if (sync.kind === "saving") return "Sending to the receiver…";
  if (sync.kind === "applied") return `Saved here and applied to the receiver (version ${sync.revision})`;
  if (sync.kind === "error") return `Saved here, but the receiver refused it: ${sync.message}`;
  return "Saved in this browser";
}

export default function App() {
  const [view, setView] = useState<View>("live");
  const [audience, setAudience] = useState(false);
  const [menu, setMenu] = useState(false);
  const [source, setSource] = useState<Source>(() => {
    try {
      return localStorage.getItem("aware-source") === "receiver" ? "receiver" : "browser";
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
  const [help, setHelp] = useState(false);
  const helpDialog = useRef<HTMLDialogElement>(null);
  const session = useSession(source, profile, labels);
  const { view: state, connection } = session;
  const connected = connection === "connected";
  const glasses = source === "receiver" && connected && state.health?.display.connected;

  const applySetup = useCallback(({ profile, display, direction }: SetupChange) => {
    setProfile(profile);
    setLabels(display.labels);
    setAppearance({
      text: display.labels ? "labels" : "icons",
      motion: display.motion === "pulse" ? "gentle" : "none",
      colors: { ...defaultAppearance.colors, ...display.colors },
      direction,
    });
  }, []);

  useEffect(() => {
    if (help) helpDialog.current?.showModal();
    else helpDialog.current?.close();
  }, [help]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setAudience(false);
        setMenu(false);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);

  const prefs = (profile?.notification_preferences ?? {
    mode: "balanced",
    event_tiers: {},
  }) as Preferences;
  // Direction is a design hypothesis: only the browser preview may simulate it.
  const direction = source === "browser" ? appearance.direction : "unknown";
  const active = state.active;
  const latest = state.decisions.at(-1);
  const focus = focusOptions.find((f) => f.key === state.focus_mode)!;
  const sourceSummary =
    source === "browser"
      ? "Test sounds in this browser"
      : connected
        ? state.health?.capture.live
          ? "Receiver, hearing audio"
          : "Receiver, waiting for audio"
        : connection === "connecting"
          ? "Connecting to the receiver…"
          : "Receiver not reachable";
  const stageCaption =
    source === "browser"
      ? direction === "unknown"
        ? "Test sound"
        : `Test sound, placed ${direction} (simulated)`
      : active
        ? sourceLabel(active.source)
        : sourceSummary;
  const go = (next: View) => {
    setView(next);
    setMenu(false);
  };

  const nav = (
    <>
      <nav className="nav" aria-label="Main">
        {(
          [
            ["live", "Live"],
            ["preferences", "Preferences"],
            ["log", "Event log"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            className="nav-item"
            aria-current={view === key ? "page" : undefined}
            onClick={() => go(key)}
          >
            {label}
            {key === "log" && state.decisions.length > 0 && (
              <span className="nav-count">{state.events.length}</span>
            )}
          </button>
        ))}
      </nav>
      <fieldset className="side-group">
        <legend>Sounds come from</legend>
        {(
          [
            ["browser", "This browser", "Test sounds, no microphone"],
            ["receiver", "Receiver", "Recorded or live audio"],
          ] as const
        ).map(([key, label, detail]) => (
          <label key={key} className="source-option">
            <input
              type="radio"
              name="source"
              value={key}
              checked={source === key}
              onChange={() => setSource(key)}
            />
            <span>
              {label}
              <small>{detail}</small>
            </span>
          </label>
        ))}
      </fieldset>
      <div className="side-group status-list">
        <div className="side-label">Status</div>
        <p>
          <span className={`dot ${source === "browser" || connected ? "on" : "off"}`} />
          {source === "browser" ? "Simulated in this browser" : sourceSummary}
        </p>
        <p>
          <span className={`dot ${glasses ? "on" : "off"}`} />
          {glasses ? "Glasses connected" : "Glasses not connected"}
        </p>
        {source === "receiver" && !connected && (
          <p className="side-hint">
            Start it with <code>python3 -m audio.server</code>
          </p>
        )}
      </div>
      <button className="side-link" onClick={() => setHelp(true)}>
        How it works
      </button>
    </>
  );

  if (audience) {
    return (
      <div className="audience">
        <Stage event={active} appearance={appearance} direction={direction} caption={stageCaption} large />
        <div className="audience-bar">
          <span>
            <span className={`dot ${source === "browser" || connected ? "on" : "off"}`} />
            {latest ? explain(latest) : sourceSummary}
          </span>
          <span className="audience-oled">
            <Oled event={active} labels={labels} />
          </span>
          <button className="button button-light" onClick={session.dismiss} disabled={!active}>
            Dismiss
          </button>
          <button className="button button-light" onClick={() => setAudience(false)}>
            <X size={15} /> Exit
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="product" href="#" onClick={(e) => (e.preventDefault(), go("live"))}>
          <Mark /> Aware
        </a>
        {nav}
      </aside>
      <header className="phone-bar">
        <a className="product" href="#" onClick={(e) => (e.preventDefault(), go("live"))}>
          <Mark /> Aware
        </a>
        <button className="icon-button" aria-label="Menu" aria-expanded={menu} onClick={() => setMenu(!menu)}>
          {menu ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>
      {menu && <div className="phone-menu">{nav}</div>}

      <main className="canvas">
        {view === "live" && (
          <>
            <div className="title-row">
              <div>
                <h1>What the wearer sees</h1>
                <p className="subline">
                  {presetName[prefs.mode]} preset · {focus.label}
                  {state.paused ? " · Paused" : ""} · {sourceSummary}
                </p>
              </div>
              <div className="title-actions">
                <button
                  className="button button-grey"
                  onClick={session.busy ? session.stopSequence : session.playSequence}
                  disabled={source === "receiver" && !connected}
                >
                  {session.busy ? "Stop" : "Play a busy minute"}
                </button>
                <button className="button button-dark" onClick={() => setAudience(true)}>
                  <Expand size={15} /> Audience view
                </button>
              </div>
            </div>

            <div className="live-grid">
              <div className="live-main">
                <Stage event={active} appearance={appearance} direction={direction} caption={stageCaption} />
                <div className="under-stage">
                  <section className="panel glasses-panel" aria-labelledby="glasses-title">
                    <h2 id="glasses-title">On the glasses</h2>
                    <div className="oled-frame">
                      <Oled event={active} labels={labels} />
                    </div>
                    <p className="note">
                      {glasses
                        ? `The connected display (${Object.keys(state.health!.display.clients).join(", ")}) shows this frame now.`
                        : "The glasses' 128 × 64 frame, pixel for pixel. Dark means nothing to show."}
                    </p>
                  </section>
                  <section className="panel now-panel" aria-labelledby="now-title" aria-live="polite">
                    <h2 id="now-title">Now</h2>
                    {active ? (
                      <>
                        <div className="now-cue">
                          <SoundIcon type={active.type} size={22} />
                          <span>
                            {active.label}
                            <small>{tierNames[active.priority_tier]}</small>
                          </span>
                        </div>
                        <Remaining event={active} remaining={state.remaining_ms} />
                      </>
                    ) : (
                      <p className="now-empty">{state.paused ? "Paused. Nothing will show." : "Nothing showing."}</p>
                    )}
                    <p className="why">{latest ? explain(latest) : "Play a sound to see how it is handled."}</p>
                    {state.queue.length > 0 && (
                      <p className="note">
                        Next when this clears:{" "}
                        {state.queue
                          .map((q) => sounds.find((s) => s.type === q.type)?.label ?? q.type)
                          .join(", ")}
                      </p>
                    )}
                    <dl className="ladder" aria-label="How long each priority stays">
                      {([4, 3, 2, 1] as const).map((tier) => (
                        <div key={tier} style={{ display: "contents" }}>
                          <dt className={active?.priority_tier === tier ? "is-active" : ""}>{tierNames[tier]}</dt>
                          <dd className={active?.priority_tier === tier ? "is-active" : ""}>
                            {tier === 4 ? "30 s, longer while it continues" : `${lifetimeMs[tier] / 1000} s`}
                          </dd>
                        </div>
                      ))}
                    </dl>
                    <button className="button button-outline" onClick={session.dismiss} disabled={!active}>
                      Dismiss
                    </button>
                  </section>
                </div>
              </div>

              <div className="live-side">
                <section aria-labelledby="sounds-title">
                  <div className="section-head">
                    <h2 id="sounds-title">Play a sound</h2>
                    <button className="quiet-link" onClick={() => go("preferences")}>
                      Change priorities
                    </button>
                  </div>
                  <ul className="sound-list">
                    {sounds.map((sound) => {
                      const tier = effectiveTier(sound.type, sound.tier, prefs);
                      const unavailable = source === "receiver" && (!connected || !sound.receiver);
                      return (
                        <li key={sound.type}>
                          <button
                            className="sound-row"
                            aria-current={active?.type === sound.type ? "true" : undefined}
                            disabled={unavailable}
                            onClick={() => void session.play(sound.type)}
                            title={
                              source === "receiver" && !sound.receiver
                                ? "The receiver has no detector for this sound"
                                : undefined
                            }
                          >
                            <SoundIcon type={sound.type} size={18} />
                            <span className="sound-name">{sound.label}</span>
                            <span className={`sound-tier ${tier === 0 ? "is-zero" : ""}`}>{tierNames[tier]}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                  {session.error && (
                    <p className="inline-error" role="alert">
                      {session.error}
                    </p>
                  )}
                </section>

                <section aria-labelledby="mode-title">
                  <h2 id="mode-title">Mode</h2>
                  <div className="segmented" role="radiogroup" aria-labelledby="mode-title">
                    {focusOptions.map((option) => (
                      <button
                        key={option.key}
                        role="radio"
                        aria-checked={state.focus_mode === option.key}
                        onClick={() => void session.setControls({ focus_mode: option.key })}
                        disabled={source === "receiver" && !connected}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                  <p className="note">{focus.detail}</p>
                  <button
                    className="button button-outline pause-button"
                    aria-pressed={state.paused}
                    onClick={() => void session.setControls({ paused: !state.paused })}
                    disabled={source === "receiver" && !connected}
                  >
                    {state.paused ? <Play size={14} /> : <Pause size={14} />}
                    {state.paused ? "Resume alerts" : "Pause all alerts"}
                  </button>
                  {state.paused && <p className="note">Paused hides every cue, urgent ones too.</p>}
                </section>

                <section aria-labelledby="recent-title">
                  <div className="section-head">
                    <h2 id="recent-title">Recent</h2>
                    {state.decisions.length > 4 && (
                      <button className="quiet-link" onClick={() => go("log")}>
                        View all
                      </button>
                    )}
                  </div>
                  {state.decisions.length === 0 ? (
                    <p className="note">No sounds yet.</p>
                  ) : (
                    <ul className="recent-list">
                      {[...state.decisions]
                        .reverse()
                        .slice(0, 4)
                        .map((d, i) => (
                          <li key={`${d.event_id}-${d.reason}-${i}`}>
                            <SoundIcon type={d.type as SoundEvent["type"]} size={15} />
                            <span>{explain(d)}</span>
                          </li>
                        ))}
                    </ul>
                  )}
                </section>
              </div>
            </div>
          </>
        )}

        <div className="preferences-view" hidden={view !== "preferences"}>
          <p className="sync-line" role="status">
            <span className={`dot ${source === "receiver" && session.sync.kind === "error" ? "off" : "on"}`} />
            {syncText(source, session.sync, connected)}
          </p>
          <Onboarding onChange={applySetup} onComplete={() => go("live")} />
        </div>

        {view === "log" && (
          <>
            <div className="title-row">
              <div>
                <h1>Event log</h1>
                <p className="subline">
                  {state.events.length} {state.events.length === 1 ? "sound" : "sounds"} this session ·{" "}
                  {sourceSummary}
                </p>
              </div>
            </div>
            {state.decisions.length === 0 ? (
              <p className="empty">Nothing yet. Sounds you play or the receiver hears will be listed here.</p>
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
                    const event = state.events.find((e) => e.event_id === d.event_id);
                    return (
                      <tr key={`${d.event_id}-${d.reason}-${i}`}>
                        <td className="num">{event ? clock(event.timestamp_ms) : "—"}</td>
                        <td>
                          <span className="log-sound">
                            <SoundIcon type={d.type as SoundEvent["type"]} size={16} />
                            {event?.label ?? d.type}
                          </span>
                        </td>
                        <td className="muted">{event ? sourceLabel(event.source) : "—"}</td>
                        <td>{tierNames[d.priority_tier]}</td>
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
              <p className="note">Scores are uncalibrated model outputs. Direction stays unknown until measured.</p>
              <pre>{JSON.stringify(state, null, 2)}</pre>
            </details>
          </>
        )}
      </main>

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
            <strong>Hear.</strong> A laptop model recognises sounds like a knock, a dog or a smoke alarm. Test
            sounds stand in for it here.
          </li>
          <li>
            <strong>Decide.</strong> One engine applies your priorities and mode, merges repeats, holds or drops
            what can wait, and remembers what you dismissed.
          </li>
          <li>
            <strong>Show.</strong> The glasses draw one small cue on a 128 × 64 display. This page shows the same
            cue for everyone watching.
          </li>
        </ol>
        <p className="note">
          Name detection and sound direction are not running yet. Show my room uses your camera only in this tab;
          nothing is recorded. Aware can miss sounds or raise false alerts, so it is not a safety device.
        </p>
        <button className="button button-dark" autoFocus onClick={() => setHelp(false)}>
          Got it
        </button>
      </dialog>
    </div>
  );
}

function Remaining({ event, remaining }: { event: SoundEvent; remaining: number }) {
  const total = lifetimeMs[event.priority_tier] || 1;
  const fraction = Math.max(0, Math.min(1, remaining / total));
  return (
    <div className="remaining">
      <div className="remaining-track" aria-hidden="true">
        <div className="remaining-fill" style={{ transform: `scaleX(${fraction})` }} />
      </div>
      <span className="num">{Math.ceil(remaining / 1000)} s left</span>
    </div>
  );
}

