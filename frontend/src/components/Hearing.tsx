import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { levelFraction, type Hearing } from "../lib/observations";

const STALE_MS = 4000;
const QUIET_DBFS = -70;
const MIC_COMMAND = ".venv/bin/python -m audio.cli mic --device 1 --endpoint http://127.0.0.1:8765/events";

function Bar({ value, threshold, strong }: { value: number; threshold?: number; strong?: boolean }) {
  return (
    <span className="hearing-track">
      <span className={`hearing-fill ${strong ? "is-strong" : ""}`} style={{ transform: `scaleX(${value})` }} />
      {threshold !== undefined && (
        <span className="hearing-threshold" style={{ left: `${threshold * 100}%` }} title={`Alert at ${threshold.toFixed(2)}`} />
      )}
    </span>
  );
}

/** What the microphone hears right now, from the receiver's observation stream (Receiver mode). */
export default function HearingPanel({ hearing }: { hearing: Hearing }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const o = hearing.latest;
  const age = hearing.receivedAt === null ? null : now - hearing.receivedAt;
  const stale = age === null || age > STALE_MS;
  const quiet = !o || o.level_dbfs <= QUIET_DBFS;
  const status = !o
    ? "Waiting for audio"
    : stale
      ? `Last heard ${Math.round((age ?? 0) / 1000)} s ago`
      : o.source === "microphone"
        ? "Microphone live"
        : o.source === "replay"
          ? "Replaying a recording"
          : `Live · ${o.source}`;
  const alerts = !stale && o ? o.emitted.map((e) => e.label) : [];

  return (
    <section className="hearing" aria-label="What the microphone hears">
      <header className="hearing-head">
        <h2>Hearing now</h2>
        <span className={`dot ${!o || stale ? "is-off" : ""}`} aria-hidden="true" />
        <span className="hearing-status">{status}</span>
        {o && !stale && <span className="hearing-meta">{o.level_dbfs > -100 ? `${o.level_dbfs} dBFS` : "silence"}</span>}
        <span className="dock-spacer" />
        <a className="key" href="/api/teach" target="_blank" rel="noreferrer">
          Teach sounds &amp; your name <ExternalLink size={13} />
        </a>
      </header>

      {!o || stale ? (
        <p className="hearing-empty">
          {o ? "Is the microphone still running? " : "Nothing heard yet. "}
          Start it in a Terminal tab from the project folder (use your mic's number from{" "}
          <code>audio.cli devices</code>):
          <code className="hearing-cmd">{MIC_COMMAND}</code>
        </p>
      ) : (
        <>
          <div className="hearing-level" aria-label={`Level ${o.level_dbfs} dBFS`}>
            <Bar value={levelFraction(o.level_dbfs)} />
          </div>
          {alerts.length > 0 && (
            <p className="hearing-alert" aria-live="polite">
              Alert sent: {alerts.join(", ")}
            </p>
          )}
          <ul className={`hearing-list ${quiet ? "is-quiet" : ""}`}>
            {o.top.slice(0, 6).map((t) => (
              <li key={t.label}>
                <span className="hearing-label">{t.label}</span>
                <Bar value={t.score} />
                <span className="hearing-num">{t.score.toFixed(2)}</span>
              </li>
            ))}
          </ul>
          {o.custom.length > 0 && (
            <>
              <h3 className="hearing-sub">Your taught sounds</h3>
              <ul className="hearing-list">
                {o.custom.map((c) => (
                  <li key={c.id}>
                    <span className="hearing-label">{c.label}</span>
                    <Bar value={c.score} threshold={c.threshold} strong={c.score >= c.threshold} />
                    <span className="hearing-num">{c.score.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {quiet && <p className="hearing-note">Quiet room: labels on near-silence aren't meaningful.</p>}
        </>
      )}
      {hearing.error && <p className="hearing-note">Observation stream unavailable: {hearing.error}</p>}
    </section>
  );
}
