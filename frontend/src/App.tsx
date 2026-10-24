import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  AudioLines,
  Check,
  ChevronRight,
  CircleHelp,
  Code2,
  Expand,
  Glasses,
  LayoutDashboard,
  List,
  LoaderCircle,
  Monitor,
  Play,
  Radio,
  Settings2,
  Sparkles,
  Unplug,
  VolumeX,
  X,
} from "lucide-react";
import Cue, { SoundIcon } from "./components/Cue";
import Scene from "./components/Scene";
import Oled from "./components/Oled";
import { defaultAppearance, type Appearance } from "./lib/appearance";
import Onboarding, { type SetupChange } from "../mana/AwareOnboarding.jsx";
import { mockPriority, type Preset } from "./lib/presets";
import {
  applyMock,
  previewMock,
  emptyMock,
  expireMock,
  makeMock,
  parseSnapshot,
  request,
  sounds,
  tierNames,
  type EventType,
  type Snapshot,
  type Tier,
} from "./lib/events";

type Mode = "mock" | "receiver";
type View = "companion" | "events" | "preferences";
const initial: Snapshot = { active: null, events: [], decisions: [] };
const sourceLabel = (source: string) =>
  ({
    microphone: "Microphone",
    mock: "Mock",
    replay: "Recording",
    simulation: "Simulation",
  })[source] ?? source;

export default function App() {
  const [mode, setMode] = useState<Mode>("mock");
  const [view, setView] = useState<View>("companion");
  const [focus, setFocus] = useState(false);
  const [preset, setPreset] = useState<Preset>("balanced");
  const [appearance, setAppearance] = useState<Appearance>(defaultAppearance);
  const [mock, setMock] = useState(emptyMock);
  const [remote, setRemote] = useState<Snapshot>(initial);
  const [connection, setConnection] = useState<
    "idle" | "connecting" | "connected" | "disconnected"
  >("idle");
  const [message, setMessage] = useState(
    "Choose a sound below. See what comes into focus.",
  );
  const [pending, setPending] = useState(false);
  const [scenario, setScenario] = useState(false);
  const [overrides, setOverrides] = useState<Partial<Record<EventType, Tier>>>(
    {},
  );
  const applySetup = useCallback(
    ({ profile, display, direction }: SetupChange) => {
      setPreset(profile.notification_preferences.mode);
      setOverrides(profile.notification_preferences.event_tiers);
      setAppearance({
        text: display.labels ? "labels" : "icons",
        motion: display.motion === "pulse" ? "gentle" : "none",
        colors: { ...defaultAppearance.colors, ...display.colors },
        direction,
      });
    },
    [],
  );
  const [help, setHelp] = useState(false);
  const helpDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (help) helpDialog.current?.showModal();
    else helpDialog.current?.close();
  }, [help]);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const state = mode === "mock" ? mock : remote;
  const connected = connection === "connected";
  const stopScenario = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setScenario(false);
  }, []);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);
  useEffect(() => {
    const timer = setInterval(
      () => setMock((s) => expireMock(s, performance.now())),
      100,
    );
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setFocus(false);
        setHelp(false);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  useEffect(() => {
    if (mode !== "receiver") return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController;
    setConnection("connecting");
    setRemote(initial);
    async function poll() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2500);
      try {
        const snapshot = parseSnapshot(
          await request("/state", undefined, controller.signal),
        );
        if (!cancelled) {
          setRemote(snapshot);
          setConnection("connected");
          setMessage((previous) =>
            previous.startsWith("Connecting to the local receiver")
              ? "Receiver ready. Replay audio or inject a labeled mock event below."
              : previous,
          );
        }
      } catch {
        if (!cancelled) {
          setConnection("disconnected");
          setRemote((s) => ({ ...s, active: null }));
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
  }, [mode]);
  const changeMode = (next: Mode) => {
    stopScenario();
    setMode(next);
    setMock(emptyMock());
    setRemote(initial);
    setConnection("idle");
    setMessage(
      next === "mock"
        ? "Simulator selected. Nothing here is a live detection."
        : "Connecting to the local receiver on port 8765.",
    );
  };
  const trigger = async (type: EventType) => {
    const event = makeMock(
      type,
      mode === "mock" ? mockPriority(type, preset, overrides) : undefined,
    );
    if (mode === "mock") {
      stopScenario();
      setMock((s) => previewMock(s, event, performance.now()));
      setMessage(
        event.priority_tier === 0
          ? `${event.label} received. Tier 0 stays quietly in the background.`
          : `${event.label} preview. Use Play sequence to test competing priorities.`,
      );
      return;
    }
    if (!connected) return;
    setPending(true);
    try {
      await request("/events", { ...event, confidence: 0.9 });
      setMessage(
        `${event.label}: mock event sent to Python. This tests delivery, not recognition.`,
      );
    } catch {
      setMessage("Event was not sent. Check the local receiver and try again.");
    } finally {
      setPending(false);
    }
  };
  const dismiss = async () => {
    stopScenario();
    if (mode === "mock") {
      setMock((s) => ({ ...s, active: null, expiresAt: 0 }));
      setMessage("Cue cleared. Your next sound has room.");
      return;
    }
    setPending(true);
    try {
      await request("/dismiss", {});
      setMessage("Dismiss sent to receiver.");
    } catch {
      setMessage("Could not dismiss the cue. Check the receiver.");
    } finally {
      setPending(false);
    }
  };
  const runScenario = () => {
    stopScenario();
    setScenario(true);
    setMock(emptyMock());
    const steps: [number, EventType][] = [
      [0, "knock"],
      [1200, "name_called"],
      [3000, "smoke_alarm"],
      [4500, "dog_bark"],
    ];
    timers.current = steps.map(([delay, type]) =>
      setTimeout(() => {
        const event = makeMock(type, mockPriority(type, preset, overrides));
        setMock((s) => applyMock(s, event, performance.now()));
        setMessage(
          `Demo sequence: ${event.label} at tier ${event.priority_tier}. Higher-priority cues remain in focus.`,
        );
      }, delay),
    );
    timers.current.push(setTimeout(() => setScenario(false), 4700));
  };
  const openMirror = () => {
    setView("companion");
    setFocus(true);
  };
  const cueSource = state.active
    ? sourceLabel(state.active.source)
    : mode === "mock"
      ? "Mock session"
      : "Receiver session";
  const statusText =
    mode === "mock"
      ? "Simulator ready"
      : connected
        ? "Receiver connected"
        : connection === "connecting"
          ? "Connecting…"
          : "Receiver disconnected";

  return (
    <div className={`app ${focus ? "focus-mode" : ""}`}>
      {!focus && (
        <aside className="rail" aria-label="Main navigation">
          <a
            className="brand-mark"
            href="#"
            aria-label="Aware home"
            onClick={(e) => {
              e.preventDefault();
              setView("companion");
            }}
          >
            <AudioLines size={25} />
          </a>
          <nav>
            <button
              className={view === "companion" ? "selected" : ""}
              onClick={() => setView("companion")}
              aria-label="Companion"
              title="Companion"
              aria-current={view === "companion" ? "page" : undefined}
            >
              <LayoutDashboard size={20} />
            </button>
            <button
              onClick={openMirror}
              aria-label="Audience mirror"
              title="Audience mirror"
            >
              <Glasses size={21} />
            </button>
            <button
              className={view === "events" ? "selected" : ""}
              onClick={() => setView("events")}
              aria-label="Event log"
              title="Event log"
              aria-current={view === "events" ? "page" : undefined}
            >
              <List size={21} />
            </button>
            <button
              className={view === "preferences" ? "selected" : ""}
              onClick={() => setView("preferences")}
              aria-label="Set up Aware"
              title="Set up Aware"
              aria-current={view === "preferences" ? "page" : undefined}
            >
              <Settings2 size={20} />
            </button>
          </nav>
          <button
            className="rail-help"
            onClick={() => setHelp(true)}
            aria-label="About this preview"
          >
            <CircleHelp size={21} />
          </button>
        </aside>
      )}
      <main>
        {!focus && (
          <header className="topbar">
            <a
              className="wordmark"
              href="#"
              onClick={(e) => {
                e.preventDefault();
                setView("companion");
              }}
            >
              aware<span> / </span>
              <small>the visual companion</small>
            </a>
            <div className="topbar-right">
              <button className="text-button" onClick={() => setHelp(true)}>
                How it works <ArrowRight size={15} />
              </button>
            </div>
          </header>
        )}
        {!focus && view !== "preferences" && (
          <div className="page-heading">
            <div>
              <h1>{view === "events" ? "Event log" : "Sound overview"}</h1>
            </div>
            <button
              className="outline-button mirror-launch"
              onClick={openMirror}
            >
              <Expand size={16} /> Open audience mirror <ArrowRight size={16} />
            </button>
          </div>
        )}

        {(view === "companion" || focus) && (
          <>
            <div className="workspace">
              <section
                className="viewport-panel"
                aria-label="Audience mirror preview"
              >
                <div className="panel-heading">
                  <div>Browser mirror</div>
                  <button
                    className="icon-button"
                    onClick={() => setFocus(!focus)}
                    aria-label={
                      focus ? "Exit audience mirror" : "Expand audience mirror"
                    }
                  >
                    {focus ? <X size={17} /> : <Expand size={16} />}
                  </button>
                </div>
                <div className="viewport">
                  <Scene />
                  <div className="scene-shade" />
                  <div className="view-top">
                    <span className="scene-tag">
                      <span
                        className={`status-dot ${mode === "receiver" && !connected ? "offline" : ""}`}
                      />
                      {mode === "mock"
                        ? `Mock preview${appearance.direction === "unknown" ? "" : " · simulated " + appearance.direction}`
                        : connected
                          ? `Receiver · ${state.active ? cueSource : "ready"}`
                          : "Disconnected"}
                    </span>
                  </div>
                  <Cue
                    event={state.active}
                    appearance={appearance}
                    direction={
                      mode === "mock" ? appearance.direction : "unknown"
                    }
                  />
                </div>
              </section>
              {!focus && (
                <aside className="right-stack">
                  <section className="device-panel">
                    <div className="device-title">
                      <span>Glasses preview</span>
                      <Glasses size={19} />
                    </div>
                    <div className="oled-screen">
                      <Oled
                        event={state.active}
                        appearance={appearance}
                        direction={
                          mode === "mock" ? appearance.direction : "unknown"
                        }
                      />
                    </div>
                    <div className="device-note">
                      <span className="outline-dot" /> Preview only · not
                      connected
                    </div>
                  </section>
                  <section className="connection-panel">
                    <div
                      className="mode-picker"
                      role="group"
                      aria-label="Event source"
                    >
                      <button
                        aria-pressed={mode === "mock"}
                        className={mode === "mock" ? "active" : ""}
                        onClick={() => changeMode("mock")}
                      >
                        <Sparkles size={14} /> Simulator
                      </button>
                      <button
                        aria-pressed={mode === "receiver"}
                        className={mode === "receiver" ? "active" : ""}
                        onClick={() => changeMode("receiver")}
                      >
                        <Radio size={14} /> Receiver
                      </button>
                    </div>
                    <div className="connection-line">
                      <span
                        className={`status-dot ${mode === "receiver" && !connected ? "offline" : ""}`}
                      />
                      <strong>{statusText}</strong>
                      {connection === "connecting" && (
                        <LoaderCircle size={14} className="spin" />
                      )}
                    </div>
                    <p>
                      {mode === "mock"
                        ? "Mock sounds. No microphone needed."
                        : connected
                          ? "Following Python alerts. Microphone status unavailable."
                          : "Start the local Python receiver, then this view reconnects automatically."}
                    </p>
                    {mode === "receiver" && !connected && (
                      <code>python3 -m audio.server</code>
                    )}
                  </section>
                </aside>
              )}
            </div>
            {!focus && (
              <section className="sound-section">
                <div className="section-heading">
                  <div>
                    <h2>Try a sound</h2>
                  </div>
                  <div className="sound-actions">
                    {mode === "mock" && (
                      <button
                        className="text-button"
                        onClick={scenario ? stopScenario : runScenario}
                      >
                        {scenario ? <X size={15} /> : <Play size={14} />}{" "}
                        {scenario ? "Stop sequence" : "Play sequence"}
                      </button>
                    )}
                    <button
                      className="outline-button"
                      onClick={dismiss}
                      disabled={pending || (!state.active && !scenario)}
                    >
                      <X size={14} /> Dismiss cue
                    </button>
                  </div>
                </div>
                <div className="sound-grid">
                  {sounds.map((sound) => (
                    <button
                      key={sound.type}
                      className={`sound-card ${state.active?.type === sound.type ? "is-current" : ""}`}
                      disabled={
                        pending ||
                        (mode === "receiver" && (!connected || !sound.receiver))
                      }
                      onClick={() => void trigger(sound.type)}
                    >
                      <span className="sound-icon">
                        <SoundIcon type={sound.type} size={19} />
                      </span>
                      <strong>{sound.label}</strong>
                    </button>
                  ))}
                </div>
                <p className="action-message" role="status">
                  <Activity size={14} />
                  {message}
                </p>
              </section>
            )}
          </>
        )}

        <div
          className="onboarding-host"
          hidden={focus || view !== "preferences"}
        >
          <button className="text-button" onClick={() => setView("companion")}>
            Back to mirror <ArrowRight size={15} />
          </button>
          <Onboarding onChange={applySetup} />
        </div>
        {!focus && view === "events" && (
          <section
            className={`activity-panel ${view === "events" ? "expanded-events" : ""}`}
          >
            <div className="activity-heading">
              <div>
                <span className="mini-dot" />{" "}
                {view === "events" ? "Event log" : "A moment in your session"}{" "}
                <span className="count">{state.events.length}</span>
              </div>
              {view !== "events" && (
                <button
                  className="text-button"
                  onClick={() => setView("events")}
                >
                  View all events <ChevronRight size={14} />
                </button>
              )}
            </div>
            {state.events.length === 0 ? (
              <div className="empty-events">
                <AudioLines size={21} />
                <span>
                  Nothing to catch up on.
                  <small>Try a sound to start your session.</small>
                </span>
                <span className="empty-line" />
              </div>
            ) : (
              <div className="event-list">
                {[...state.events]
                  .reverse()
                  .slice(0, view === "events" ? 50 : 3)
                  .map((event) => {
                    const decision = state.decisions.find(
                      (d) => d.event_id === event.event_id,
                    );
                    return (
                      <div className="event-row" key={event.event_id}>
                        <span className="event-icon">
                          <SoundIcon type={event.type} size={18} />
                        </span>
                        <strong>
                          {event.label}
                          <small>{sourceLabel(event.source)}</small>
                        </strong>
                        <span className="event-reason">
                          {decision?.reason === "displayed"
                            ? "Brought into focus"
                            : decision?.reason === "ignored_tier_zero"
                              ? "Kept in background"
                              : decision?.reason === "suppressed_lower_priority"
                                ? "Higher-priority cue active"
                                : (decision?.reason ?? "Received")}
                        </span>
                        <span className="event-tier">
                          {tierNames[event.priority_tier]}
                        </span>
                        <time>
                          {new Date(event.timestamp_ms).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </time>
                      </div>
                    );
                  })}
              </div>
            )}
            {view === "events" && (
              <details className="diagnostics">
                <summary>
                  <Code2 size={15} /> Developer details
                </summary>
                <p>
                  Scores are uncalibrated model outputs. Unknown direction is
                  intentionally omitted from the cue.
                </p>
                <pre>{JSON.stringify(state, null, 2)}</pre>
              </details>
            )}
          </section>
        )}
        {focus && (
          <div className="mirror-controls">
            <span>
              <span className="status-dot" />
              {cueSource} · {statusText}
            </span>
            <button
              className="outline-button"
              onClick={dismiss}
              disabled={pending || !state.active}
            >
              Dismiss cue
            </button>
            <button className="outline-button" onClick={() => setFocus(false)}>
              Exit mirror <X size={14} />
            </button>
          </div>
        )}
      </main>
      <dialog
        ref={helpDialog}
        onCancel={() => setHelp(false)}
        onClose={() => setHelp(false)}
        aria-labelledby="about-title"
        className="about-dialog"
      >
        <button
          className="dialog-close icon-button"
          autoFocus
          onClick={() => setHelp(false)}
          aria-label="Close help"
        >
          <X size={20} />
        </button>
        <h2 id="about-title">Sound, made visible.</h2>
        <p>
          A browser companion for situational awareness glasses. A judge wears
          the display while the audience follows the same active cue.
        </p>
        <div className="about-step">
          <Monitor size={20} />
          <span>
            <strong>Simulator</strong>Mock cues explore the design. Name
            detection and spatial audio are not running here.
          </span>
        </div>
        <div className="about-step">
          <Radio size={20} />
          <span>
            <strong>Receiver</strong>Connects to Python on port 8765. Recorded
            or microphone events appear as they arrive. The UI never starts your
            microphone.
          </span>
        </div>
        <div className="about-step">
          <Unplug size={20} />
          <span>
            <strong>Hardware</strong>The OLED is a design preview until a
            physical display adapter is connected.
          </span>
        </div>
        <div className="about-step">
          <VolumeX size={20} />
          <span>
            <strong>Not a safety device</strong>Recognition can miss sounds or
            produce false alerts. Treat this as an experimental awareness aid.
          </span>
        </div>
        <button className="dark-button" onClick={() => setHelp(false)}>
          <Check size={16} /> Got it
        </button>
      </dialog>
    </div>
  );
}
