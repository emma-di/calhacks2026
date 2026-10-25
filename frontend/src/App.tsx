import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { Expand, Mic, Pause, Play, X } from "lucide-react";
import { SoundIcon } from "./components/Cue";
import Oled from "./components/Oled";
import Stage from "./components/Stage";
import { defaultAppearance, type Appearance } from "./lib/appearance";
import Onboarding, {
  type ManaProfile,
  type SetupChange,
} from "../mana/AwareOnboarding.jsx";
import { effectiveTier, type FocusMode, type Preferences } from "./lib/alerts";
import {
  soundCatalog,
  sounds,
  tierNames,
  type Health,
  type Observation,
  type SoundEvent,
} from "./lib/events";
import { explain, outcome } from "./lib/explain";
import { useSession, type Source, type SyncStatus } from "./lib/session";
import { useHearing } from "./lib/observations";
import HearingPanel from "./components/Hearing";
import TeachPanel from "./components/TeachPanel";
import PiMicrophoneLevels from "./components/PiMicrophoneLevels";
import { initialView, SETUP_COMPLETE_KEY } from "./lib/setupEntry";
import { HOSTED, REPO_URL } from "./lib/hosted";
import { useBrowserHearing } from "./lib/useBrowserHearing";
import type { PickedSound } from "./lib/browserHearing";

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
  // The lens of the glasses with a web in its corner.
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
      {/* A small web in the lens corner: the sense that something is happening. */}
      <g stroke="var(--signal)" strokeWidth="1" fill="none" strokeLinecap="round">
        <path d="M24 2 L13 2 M24 2 L15 9 M24 2 L24 13" />
        <path d="M19 2 Q20 4 21 5.5 Q22.5 6 24 6.5 M15.5 2 Q17 6 18 8 Q21 9 24 10" />
      </g>
    </svg>
  );
}

function syncText(source: Source, sync: SyncStatus, connected: boolean) {
  if (source === "browser") return "Saved in this browser.";
  if (!connected)
    return "Saved in this browser. New edits apply when the receiver connects.";
  if (sync.kind === "saving") return "Sending to the receiver…";
  if (sync.kind === "applied")
    return `Saved and applied to the receiver (version ${sync.revision}).`;
  if (sync.kind === "error")
    return `Saved here, but the receiver refused it: ${sync.message}`;
  return "Saved in this browser.";
}

const ruleLabel = (type: string) =>
  soundCatalog.find((c) => c.type === type)?.label ?? type.replaceAll("_", " ");

// Why a rule did or didn't fire, for the rules close enough to matter.
function ruleNote(
  type: string,
  rule: { score: number; threshold: number; reason: string },
) {
  const name = ruleLabel(type);
  const value = `${rule.score.toFixed(2)} / ${rule.threshold.toFixed(2)}`;
  if (rule.reason === "emitted") return `${name} sent (${value})`;
  if (rule.reason === "cooldown") return `${name} heard again, cooling down`;
  if (rule.reason.startsWith("suppressed"))
    return `${name} held back by alarm context`;
  if (rule.reason === "below_threshold")
    return `${name} close, below threshold (${value})`;
  return `${name}: ${rule.reason.replaceAll("_", " ")}`;
}

// Live recognizer view: every analysis window, before the receiver decides anything.
function SignalPanel({
  observations,
  health,
}: {
  observations: Observation[];
  health: Health | null;
}) {
  const listening = health?.capture.listening;
  return (
    <section className="signal-panel" aria-labelledby="signal-title">
      <h2 id="signal-title">What it's hearing</h2>
      <p className="aside">
        {listening
          ? `Listening (${health?.capture.listening_source ?? "recognizer"}) · newest first, one row per second of audio`
          : "Not listening. Start the microphone, a recording or a scene (audio/scene.py) to see live recognition."}
      </p>
      {observations.length > 0 && (
        <ol className="signal-list">
          {[...observations]
            .reverse()
            .slice(0, 8)
            .map((o) => {
              const notes = Object.entries(o.rules)
                .filter(
                  ([, r]) =>
                    r.reason === "emitted" ||
                    r.reason === "cooldown" ||
                    r.reason.startsWith("suppressed") ||
                    (r.reason === "below_threshold" &&
                      r.score >= 0.5 * r.threshold),
                )
                .map(([type, r]) => ruleNote(type, r));
              return (
                <li key={o.seq}>
                  <span
                    className="signal-level"
                    aria-label={`level ${o.level_dbfs} dBFS`}
                  >
                    <span
                      style={{
                        width: `${Math.max(2, Math.min(100, (o.level_dbfs + 70) * (100 / 70)))}%`,
                      }}
                    />
                  </span>
                  <span className="signal-top">
                    {o.top
                      .slice(0, 3)
                      .map((t) => `${t.label} ${t.score.toFixed(2)}`)
                      .join(" · ")}
                  </span>
                  <span
                    className={
                      notes.some((n) => n.includes(" sent"))
                        ? "signal-note is-sent"
                        : "signal-note"
                    }
                  >
                    {notes.length
                      ? notes.join("; ")
                      : "No alert sound near its threshold"}
                  </span>
                </li>
              );
            })}
        </ol>
      )}
    </section>
  );
}

export default function App() {
  const [setupComplete, setSetupComplete] = useState(() => {
    try { return localStorage.getItem(SETUP_COMPLETE_KEY) === "true"; }
    catch { return false; }
  });
  const [view, setView] = useState<View>(() => {
    return initialView(window.location.search, setupComplete || HOSTED);   // the online demo opens on Live
  });
  const [audience, setAudience] = useState(false);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [view, audience]);
  const [source, setSource] = useState<Source>(() => {
    if (HOSTED) return "browser";
    try {
      return localStorage.getItem("aware-source") === "browser" ? "browser" : "receiver";
    } catch {
      return "receiver";
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
  const [editRevision, setEditRevision] = useState(0);
  const [appearance, setAppearance] = useState<Appearance>(defaultAppearance);
  const [labels, setLabels] = useState(false);
  const [testDirection, setTestDirection] = useState<number | null>(null);
  const [help, setHelp] = useState(false);
  const [recordingsOpened, setRecordingsOpened] = useState(false);
  const helpDialog = useRef<HTMLDialogElement>(null);
  const session = useSession(source, profile, labels, editRevision);
  const { view: state, connection } = session;
  // Browser mode can listen with this device's microphone, only after an explicit click.
  const [micOn, setMicOn] = useState(false);
  // A name typed in the Live card counts when setup has none, so "Hey <name>" works straight away.
  const [demoName, setDemoName] = useState("");
  const setupNames = profile
    ? [profile.name_detection.primary_name, ...profile.name_detection.aliases].filter(Boolean)
    : [];
  const listenNames = setupNames.length ? setupNames : demoName.trim() ? [demoName.trim()] : [];
  const callName = listenNames[0] || "your name";
  const mic = useBrowserHearing(
    source === "browser" && micOn,
    listenNames,
    (profile?.custom_sound_requests ?? []) as PickedSound[],
    session.hear,
  );
  const connected = connection === "connected";
  const glasses = Boolean(
    source === "receiver" && connected && state.health?.display.connected,
  );
  const offline = source === "receiver" && !connected;
  const hearing = useHearing(source === "receiver" && connected);

  const applySetup = useCallback(
    ({ profile, display, direction, editRevision }: SetupChange) => {
      setProfile(profile);
      setEditRevision(editRevision);
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
  // The full sentence stays readable here after the short version clears from the glasses.
  const lastQuestion = [...state.events].reverse().find((e) => e.type === "question" && e.transcript);
  const heard = lastQuestion && (
    <p className="heard">
      Heard: “{lastQuestion.transcript}”{" "}
      <span className="muted">
        · {clock(lastQuestion.timestamp_ms)}
        {lastQuestion.summary_source === "claude" ? " · shortened by Claude" : ""}
      </span>
    </p>
  );
  const focus = focusOptions.find((f) => f.key === state.focus_mode)!;
  const sourceSummary =
    source === "browser"
      ? "Test sounds"
      : connected
        ? state.health?.capture.listening
          ? "Listening"
          : state.health?.capture.live
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
      : source === "browser" ? "Quiet. Tap a sound below and watch it reach the lens." : "Quiet.";
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
          <div>
            <p className="narration">{narration}</p>
            {heard}
          </div>
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
          <Mark /> spidey sense
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
          {HOSTED && (
            <a className="pill pill-button" href={REPO_URL} target="_blank" rel="noreferrer">
              Online demo · run it with real mics
            </a>
          )}
          {!HOSTED && <div
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
          </div>}
          {source === "browser" && (
            <button className={`pill pill-button listen-pill ${micOn ? "is-on" : ""}`} aria-pressed={micOn}
              onClick={() => { setView("live"); setMicOn((on) => !on); }}>
              <span className="dot" /> {micOn ? "Stop listening" : "Listen with your mic"}
            </button>
          )}
          {/* Live status only matters on the Live view. */}
          {view === "live" && <span
            className={`pill ${offline ? "is-off" : "is-on"}`}
            title={sourceSummary}
          >
            <span className="dot" />
            {sourceSummary}
          </span>}
          {!HOSTED && view === "live" && <span className={`pill ${glasses ? "is-on" : "is-off"}`}>
            <span className="dot" />
            {glasses ? "Display client connected" : "Glasses not connected"}
          </span>}
          <button
            className="pill pill-button"
            onClick={() => setAudience(true)}
          >
            <Expand size={13} /> Audience view
          </button>
          <button
            className="help-button"
            onClick={() => setHelp(true)}
            aria-label="How Spidey Sense works"
          >
            ?
          </button>
        </div>
      </header>

      <div className="mobile-session" role="status" hidden={view !== "live"}>
        <span>
          {sourceSummary}
          {HOSTED ? "" : ` · ${glasses ? "Display client online" : "Glasses not connected"}`}
        </span>
        <button className="key" onClick={() => setAudience(true)}>
          <Expand size={14} /> Audience view
        </button>
      </div>

      {view === "live" && (
        <main className="live">
          <h1 className="sr-only">What the wearer sees</h1>
          {source === "browser" && (
            // The demo's main action: hear it with your own microphone.
            <section className="listen-cta" aria-label="Try it with your microphone">
              <div className="listen-cta-main">
                <h2>Hear it yourself</h2>
                {!setupNames.length && (
                  <label className="listen-name">
                    Your name
                    <input value={demoName} onChange={(e) => setDemoName(e.target.value)} placeholder="e.g. Emma" autoComplete="given-name" />
                  </label>
                )}
                <button className={`listen-cta-button ${micOn ? "is-on" : ""}`} onClick={() => setMicOn((on) => !on)}>
                  <Mic size={20} /> {micOn ? "Stop listening" : "Listen with your mic"}
                </button>
                {micOn && <p className="listen-status" role="status">{mic.status === "listening" ? `Listening${mic.heard.length ? ` · hearing ${mic.heard.join(", ")}` : "…"}` : mic.status === "error" ? `Microphone unavailable: ${mic.error}` : "Starting the microphone…"}</p>}
              </div>
              <div className="listen-tries">
                <h3>Things to try</h3>
                <ul>
                  <li>Say <q>Hey {callName}, are you coming to lunch?</q> Your name shows, then the question.</li>
                  <li>Say <q>Excuse me</q> or <q>Watch out!</q></li>
                  <li>Knock on your desk, or play a dog bark or siren from your phone.</li>
                </ul>
              </div>
            </section>
          )}
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
                  ? `${tierNames[active.priority_tier]} · ${Math.ceil(state.remaining_ms / 1000)} s left${waiting ? ` · next: ${waiting}` : ""}`
                  : [state.paused && "Paused", state.focus_mode !== "everyday" && focus.label,
                     prefs.mode !== "balanced" && `${presetName[prefs.mode]} preset`].filter(Boolean).join(" · ")}
              </p>
              {heard}
            </div>
            {oledInset}
          </div>


          <section className="dock" aria-label="Controls">
            {source === "browser" && (
              <div className="browser-mic">
                <button className="key" aria-pressed={micOn} onClick={() => setMicOn((on) => !on)}>
                  {micOn ? "Stop listening" : "Listen with this device's mic"}
                </button>
                <span className="aside" role="status">
                  {mic.status === "starting" ? "Starting the microphone…"
                    : mic.status === "error" ? `Microphone unavailable: ${mic.error}`
                    : mic.status === "listening" ? `Listening${mic.heard.length ? ` · hearing ${mic.heard.join(", ")}` : ""}${mic.speech === "unavailable" ? " · name detection needs Chrome, Edge or Safari" : ""}`
                    : "Or tap a test sound."}
                </span>
                <p className="aside browser-mic-note">
                  Sounds are recognized on this device. Names and questions use your browser's speech
                  service, which sends speech to its provider (Google in Chrome). Nothing is saved here.
                  No arrows: one microphone can't tell direction.
                </p>
              </div>
            )}
            {/* Test sounds are for Browser mode; Receiver mode shows only what the microphones hear. */}
            {source === "browser" && <div className="keys" role="group" aria-label="Play a sound">
              {sounds.map((sound) => {
                const tier = effectiveTier(sound.type, sound.tier, prefs);
                return (
                  <button
                    key={sound.type}
                    className="key sound-key"
                    aria-current={
                      active?.type === sound.type ? "true" : undefined
                    }
                    onClick={() => void session.play(sound.type, testDirection)}
                  >
                    <SoundIcon type={sound.type} size={32} />
                    <span>{sound.label}</span>
                    <small className={`tier tier-${tier}`}>
                      {tierNames[tier]}
                    </small>
                  </button>
                );
              })}
            </div>}
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
            {source === "browser" && <details className="demo-tools">
              <summary>Test a direction or sequence</summary>
              <div className="dock-row">
                {" "}
                <label>
                  Simulated bearing{" "}
                  <select
                    aria-label="Simulated direction of the next test sound"
                    value={
                      testDirection === null ? "unknown" : String(testDirection)
                    }
                    onChange={(e) =>
                      setTestDirection(
                        e.target.value === "unknown"
                          ? null
                          : Number(e.target.value),
                      )
                    }
                  >
                    <option value="unknown">No direction</option>
                    {Array.from({ length: 16 }, (_, i) => {
                      const angle = i * 22.5;
                      const signed = angle > 180 ? angle - 360 : angle;
                      const side =
                        angle === 0
                          ? "Front"
                          : angle === 90
                            ? "Right"
                            : angle === 180
                              ? "Behind"
                              : angle === 270
                                ? "Left"
                                : `${signed}°`;
                      return (
                        <option key={i} value={signed}>
                          {side} · simulated
                        </option>
                      );
                    })}
                  </select>
                </label>
                <button
                  className="key"
                  onClick={
                    session.busy ? session.stopSequence : session.playSequence
                  }
                  disabled={offline}
                >
                  {session.busy ? "Stop" : "Play a busy minute"}
                </button>
              </div>
            </details>}
          </section>
        </main>
      )}

      <div className="page preferences-view" hidden={view !== "preferences"}>
        {/* Saving is automatic; the line appears only when edits are not reaching the receiver. */}
        <p className="sync-line" role="status">
          {source === "receiver" && (!connected || session.sync.kind === "error") && (
            <>
              <span className="dot is-off" />
              {syncText(source, session.sync, connected)}
            </>
          )}
        </p>
        <Onboarding
          theme="dark"
          firstUse={!setupComplete}
          canFinish={source === "browser" || session.sync.kind === "applied"}
          receiverProfile={session.receiverProfile}
          onChange={applySetup}
          onComplete={() => {
            try { localStorage.setItem(SETUP_COMPLETE_KEY, "true"); } catch { /* This visit still proceeds. */ }
            setSetupComplete(true);
            setView("live");
          }}
        />
        {!HOSTED && <details
          className="personal-recordings"
          onToggle={(event) => {
            if (event.currentTarget.open) setRecordingsOpened(true);
          }}
        >
          <summary>Personal recordings (optional)</summary>
          <p className="aside">
            For a particular sound or a name that needs help. The built-in sound
            library works without recordings.
          </p>
          {/* Keep the mounted recorder alive when the disclosure closes or views change. */}
          {recordingsOpened && <TeachPanel />}
        </details>}
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
                      <td className="muted">
                        {explain(d)}
                        {event?.transcript ? ` “${event.transcript}”` : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
          {/* Diagnostics live here so the Live view shows only what the wearer sees. */}
          <section className="diagnostics" aria-labelledby="diagnostics-title">
            <h2 id="diagnostics-title">Diagnostics</h2>
            {source === "receiver" && (
              <HearingPanel
                hearing={hearing}
                onManageSounds={() => setView("preferences")}
              />
            )}
            <SignalPanel
              observations={state.observations}
              health={state.health}
            />
            {source === "receiver" && <PiMicrophoneLevels />}
            <div className="dock-row" aria-label="Testing controls">
                <button
                  className="key"
                  aria-pressed={state.repeat_suppression === false}
                  title="Testing only: bypass recognition cooldowns and redisplay repeated detections. Priority and pause still apply."
                  disabled={offline}
                  onClick={() =>
                    void session.setControls({
                      repeat_suppression: state.repeat_suppression === false,
                    })
                  }
                >
                  {state.repeat_suppression === false
                    ? "Show every detection: on"
                    : "Show every detection: off"}
                </button>
                {source === "receiver" && (
                  <button
                    className="key"
                    aria-pressed={state.snap_to_dismiss === true}
                    disabled={offline}
                    title="Experimental microphone control: one strongly recognized finger snap dismisses the current cue. No camera needed."
                    onClick={() =>
                      void session.setControls({
                        snap_to_dismiss: !state.snap_to_dismiss,
                      })
                    }
                  >
                    {state.snap_to_dismiss
                      ? "Snap to dismiss: on"
                      : "Snap to dismiss: off"}
                  </button>
                )}
            </div>
          </section>
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
        <h2 id="about-title">How Spidey Sense works</h2>
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
          backdrop from this device; nothing is recorded. Spidey Sense can miss sounds
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
