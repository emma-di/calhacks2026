import { useCallback, useEffect, useState } from "react";
import { Mic, Square, Trash2 } from "lucide-react";
import MicMeter from "./MicMeter";
import { startRecording, type Recording } from "../lib/recorder";
import { tierNames } from "../lib/events";

// Teaching runs on the receiver's audio routes (docs/custom-sounds.md, docs/name-detection.md).
interface SoundMeta {
  id: string;
  label: string;
  priority_tier: number;
  enabled: boolean;
  status: string;
  clip_count: number;
  training: {
    training_recall?: number;
    threshold?: number;
    error?: string;
  } | null;
}
interface Background {
  base_windows: number;
  room_windows: number;
  room_clips: number;
  ready: boolean;
}
interface NameState {
  primary_name: string;
  enabled: boolean;
  learned_spellings: { text: string }[];
}
type Target = "clip" | "room" | "name" | "test";
const LIMITS: Record<Target, { seconds: number; label: string }> = {
  clip: { seconds: 8, label: "Recording the sound: make it once, then stop" },
  test: { seconds: 8, label: "Testing: make the sound once" },
  room: { seconds: 10, label: "Recording the room as it normally sounds" },
  name: { seconds: 5, label: "Recording: someone says your name once" },
};

async function api<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const init: RequestInit = { method, cache: "no-store" };
  if (body instanceof Blob) init.headers = { "Content-Type": "audio/wav" };
  else if (body !== undefined)
    init.headers = { "Content-Type": "application/json" };
  if (body !== undefined)
    init.body = body instanceof Blob ? body : JSON.stringify(body);
  const response = await fetch(`/api${path}`, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error((data as { error?: string }).error ?? response.statusText);
  return data as T;
}

export default function TeachPanel() {
  const [sounds, setSounds] = useState<SoundMeta[]>([]);
  const [background, setBackground] = useState<Background | null>(null);
  const [name, setName] = useState<NameState | null>(null);
  const [draft, setDraft] = useState({ label: "", tier: 2 });
  const [current, setCurrent] = useState<string | null>(null);
  const [recording, setRecording] = useState<{
    target: Target;
    rec: Recording;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{
    text: string;
    tone?: "ok" | "bad";
  } | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [list, profile] = await Promise.all([
        api<{ sounds: SoundMeta[]; background: Background }>(
          "GET",
          "/custom-sounds",
        ),
        api<{ name_detection: NameState }>("GET", "/profile"),
      ]);
      setSounds(list.sounds);
      setBackground(list.background);
      setName(profile.name_detection);
    } catch (e) {
      setMessage({
        text: `Teaching unavailable: ${(e as Error).message}`,
        tone: "bad",
      });
    }
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  const sound = sounds.find((s) => s.id === current) ?? null;

  /** Start a recording, or stop the one in progress (second click). Uploads when it ends. */
  async function record(target: Target, upload: (wav: Blob) => Promise<void>) {
    if (recording) return recording.rec.stop();
    let rec: Recording;
    try {
      rec = await startRecording(LIMITS[target].seconds);
    } catch (e) {
      return setMessage({
        text: `Microphone unavailable: ${(e as Error).message}`,
        tone: "bad",
      });
    }
    setMessage(null);
    setRecording({ target, rec });
    const wav = await rec.done;
    setRecording(null);
    setBusy(true);
    try {
      await upload(wav);
    } catch (e) {
      setMessage({ text: (e as Error).message, tone: "bad" });
    } finally {
      setBusy(false);
      void refresh();
    }
  }

  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    try {
      await work();
    } catch (e) {
      setMessage({ text: (e as Error).message, tone: "bad" });
    } finally {
      setBusy(false);
      void refresh();
    }
  };

  const recButton = (
    target: Target,
    idle: string,
    upload: (wav: Blob) => Promise<void>,
    disabled = false,
  ) => {
    const active = recording?.target === target;
    return (
      <button
        className={`key ${active ? "is-recording" : ""}`}
        disabled={busy || disabled || (recording !== null && !active)}
        onClick={() => void record(target, upload)}
      >
        {active ? <Square size={13} /> : <Mic size={14} />}
        {active ? "Stop" : idle}
      </button>
    );
  };

  return (
    <section className="teach" id="teach" aria-label="Personal recordings">
      <header className="hearing-head">
        <h2>Personal recordings</h2>
        <span className="hearing-status">
          Recordings are sent to your processing computer and kept locally.
        </span>
      </header>

      <p className="teach-note">
        Supported sounds need no recordings. Use these optional tools to
        recognize one particular sound or improve how your name is heard.
      </p>
      {recording && (
        <MicMeter
          analyser={recording.rec.analyser}
          startedAt={recording.rec.startedAt}
          maxSeconds={recording.rec.maxSeconds}
          label={LIMITS[recording.target].label}
        />
      )}
      {message && (
        <p
          className={`teach-message ${message.tone ? `is-${message.tone}` : ""}`}
        >
          {message.text}
        </p>
      )}

      <div className="teach-grid">
        <div className="teach-card">
          <h3>A particular sound</h3>
          {!sound ? (
            <div className="teach-row">
              <input
                aria-label="Personal sound name"
                placeholder="e.g. My front doorbell"
                maxLength={60}
                value={draft.label}
                onChange={(e) => setDraft({ ...draft, label: e.target.value })}
              />
              <select
                aria-label="Personal sound priority"
                value={draft.tier}
                onChange={(e) =>
                  setDraft({ ...draft, tier: Number(e.target.value) })
                }
              >
                {[1, 2, 3, 4].map((t) => (
                  <option key={t} value={t}>
                    {tierNames[t]}
                  </option>
                ))}
              </select>
              <button
                className="key"
                disabled={busy || !draft.label.trim()}
                onClick={() =>
                  void run(async () => {
                    const meta = await api<SoundMeta>(
                      "POST",
                      "/custom-sounds",
                      {
                        label: draft.label,
                        priority_tier: draft.tier,
                      },
                    );
                    setCurrent(meta.id);
                    setDraft({ label: "", tier: 2 });
                    setMessage({
                      text: `Record "${meta.label}" about 5 times.`,
                    });
                  })
                }
              >
                Start
              </button>
            </div>
          ) : (
            <>
              <p className="teach-note">
                <b>{sound.label}</b> · {sound.clip_count} recording
                {sound.clip_count === 1 ? "" : "s"} ·{" "}
                {sound.status.replace("_", " ")}
              </p>
              <div className="teach-dots" aria-hidden="true">
                {Array.from(
                  { length: Math.max(5, sound.clip_count) },
                  (_, i) => (
                    <span
                      key={i}
                      className={i < sound.clip_count ? "is-on" : ""}
                    />
                  ),
                )}
              </div>
              <div className="teach-row">
                {recButton("clip", "Record", async (wav) => {
                  const meta = await api<SoundMeta>(
                    "POST",
                    `/custom-sounds/${sound.id}/clips`,
                    wav,
                  );
                  setMessage({ text: `Saved recording ${meta.clip_count}.` });
                })}
                <button
                  className="key"
                  disabled={busy || recording !== null || sound.clip_count < 3}
                  onClick={() =>
                    void run(async () => {
                      setMessage({ text: "Training…" });
                      const meta = await api<SoundMeta>(
                        "POST",
                        `/custom-sounds/${sound.id}/train`,
                        {},
                      );
                      setMessage({
                        text:
                          meta.status === "ready"
                            ? "Personal detector trained. Try a fresh recording to check whether it recognizes your sound."
                            : "Training finished. Check its status before testing.",
                        tone: meta.status === "ready" ? "ok" : undefined,
                      });
                    })
                  }
                >
                  Train
                </button>
                {recButton(
                  "test",
                  "Test",
                  async (wav) => {
                    const r = await api<{
                      detected: boolean;
                      score: number;
                      threshold: number;
                    }>("POST", `/custom-sounds/${sound.id}/test`, wav);
                    setMessage(
                      r.detected
                        ? {
                            text: `Recognized (score ${r.score.toFixed(2)} ≥ ${r.threshold.toFixed(2)}).`,
                            tone: "ok",
                          }
                        : {
                            text: `Not recognized (score ${r.score.toFixed(2)} < ${r.threshold.toFixed(2)}). Add a few recordings and train again.`,
                            tone: "bad",
                          },
                    );
                  },
                  sound.status !== "ready",
                )}
                <button
                  className="key"
                  disabled={recording !== null}
                  onClick={() => setCurrent(null)}
                >
                  Done
                </button>
              </div>
            </>
          )}
        </div>

        <div className="teach-card">
          <h3>Your name</h3>
          {name?.primary_name ? (
            <>
              <p className="teach-note">
                Name set to <b>{name.primary_name}</b>
                {name.enabled ? "" : " (recognition turned off)"}. Samples are
                optional: if your name is being missed, have a friend say it
                once per recording. Two or three samples can help with
                pronunciation.
              </p>
              <div className="teach-row">
                {recButton("name", "Record name", async (wav) => {
                  const r = await api<{
                    heard: string;
                    spelling: string;
                    added: boolean;
                    note: string | null;
                    warning: string | null;
                  }>("POST", "/profile/name-samples", wav);
                  setMessage(
                    !r.added
                      ? { text: `Heard "${r.heard}". ${r.note ?? ""}` }
                      : r.warning
                        ? {
                            text: `Added "${r.spelling}". Note: ${r.warning}.`,
                            tone: "bad",
                          }
                        : {
                            text: `Heard "${r.heard}". Added "${r.spelling}".`,
                            tone: "ok",
                          },
                  );
                })}
                {name.learned_spellings.length > 0 && (
                  <button
                    className="key"
                    disabled={busy || recording !== null}
                    onClick={() =>
                      void run(
                        async () =>
                          void (await api("DELETE", "/profile/name-samples")),
                      )
                    }
                  >
                    Clear
                  </button>
                )}
              </div>
              {name.learned_spellings.length > 0 && (
                <p className="teach-note">
                  Also heard as:{" "}
                  {name.learned_spellings.map((l) => l.text).join(", ")}
                </p>
              )}
            </>
          ) : (
            <p className="teach-note">
              Type your name in Preferences. Recording it here is optional if
              recognition needs help.
            </p>
          )}
        </div>

        <div className="teach-card">
          <h3>Room background</h3>
          <p className="teach-note">
            Optional for personal sound training: record 10 seconds of the room
            without your target sound. This retrains your personal detectors to
            distinguish that background. Built-in sounds do not need it.{" "}
            {background &&
              (background.room_clips
                ? `${background.room_clips} recorded.`
                : "None yet.")}
          </p>
          <div className="teach-row">
            {recButton("room", "Record room", async (wav) => {
              const r = await api<{ retrained: unknown[] }>(
                "POST",
                "/background/clips",
                wav,
              );
              setMessage({
                text: `Room added. Retrained ${r.retrained.length} sound(s).`,
                tone: "ok",
              });
            })}
            {background?.room_clips ? (
              <button
                className="key"
                disabled={busy || recording !== null}
                onClick={() =>
                  void run(
                    async () => void (await api("DELETE", "/background")),
                  )
                }
              >
                Clear
              </button>
            ) : null}
          </div>
          {background &&
            !background.base_windows &&
            !background.room_windows && (
              <p className="teach-note">
                No personal background recorded. This does not prevent built-in
                sound recognition.
              </p>
            )}
        </div>
      </div>

      {sounds.length > 0 && (
        <ul className="teach-sounds">
          {sounds.map((s) => (
            <li key={s.id}>
              <b>{s.label}</b>
              <span className="teach-note">
                {tierNames[s.priority_tier]} · {s.clip_count} recordings ·{" "}
                {s.status.replace("_", " ")}
              </span>
              <span className="dock-spacer" />
              <label className="teach-toggle">
                <input
                  type="checkbox"
                  checked={s.enabled}
                  onChange={(e) =>
                    void run(
                      async () =>
                        void (await api("PATCH", `/custom-sounds/${s.id}`, {
                          enabled: e.target.checked,
                        })),
                    )
                  }
                />
                On
              </label>
              <button
                className="key"
                disabled={recording !== null}
                onClick={() => setCurrent(s.id)}
              >
                Teach more
              </button>
              <button
                className="key"
                aria-label={`Delete ${s.label}`}
                disabled={busy || recording !== null}
                onClick={() =>
                  void run(async () => {
                    await api("DELETE", `/custom-sounds/${s.id}`);
                    if (current === s.id) setCurrent(null);
                  })
                }
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
