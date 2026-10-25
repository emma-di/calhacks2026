import { useEffect, useState } from "react";
import { levelFraction, type Hearing } from "../lib/observations";

const STALE_MS = 4000;
const QUIET_DBFS = -70;
const MIC_COMMAND =
  ".venv/bin/python -m audio.cli mic --device 1 --endpoint http://127.0.0.1:8766/events";

const RULE_REASONS: Record<string, string> = {
  disabled: "Off",
  below_threshold: "Below detection threshold",
  cooldown: "Recognized · waiting for repeat cooldown",
  emitted: "Recognized · sent to alert engine",
  suppressed_current_context: "Filtered by current sound context",
  suppressed_recent_context: "Filtered by recent sound context",
};

function Bar({
  value,
  threshold,
  strong,
}: {
  value: number;
  threshold?: number;
  strong?: boolean;
}) {
  return (
    <span className="hearing-track">
      <span
        className={`hearing-fill ${strong ? "is-strong" : ""}`}
        style={{ transform: `scaleX(${value})` }}
      />
      {threshold !== undefined && (
        <span
          className="hearing-threshold"
          style={{ left: `${threshold * 100}%` }}
          title={`Alert at ${threshold.toFixed(2)}`}
        />
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
        <span
          className={`dot ${!o || stale ? "is-off" : ""}`}
          aria-hidden="true"
        />
        <span className="hearing-status">{status}</span>
        {o && !stale && (
          <span className="hearing-meta">
            {o.level_dbfs > -100 ? `${o.level_dbfs} dBFS` : "silence"}
          </span>
        )}
        <span className="dock-spacer" />
        <a className="key" href="#teach">
          Teach sounds &amp; your name
        </a>
      </header>

      {!o || stale ? (
        <p className="hearing-empty">
          {o ? "Is the microphone still running? " : "Nothing heard yet. "}
          Start it in a Terminal tab from the project folder (use your mic's
          number from <code>audio.cli devices</code>):
          <code className="hearing-cmd">{MIC_COMMAND}</code>
        </p>
      ) : (
        <>
          <div
            className="hearing-level"
            aria-label={`Level ${o.level_dbfs} dBFS`}
          >
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
                <span className="hearing-label" title={t.label}>
                  {t.label}
                </span>
                <Bar value={t.score} />
                <span className="hearing-num">{t.score.toFixed(2)}</span>
              </li>
            ))}
          </ul>
          {o.custom.length > 0 && (
            <>
              <h3 className="hearing-sub">Your selected sounds</h3>
              <ul className="hearing-list">
                {o.custom.map((c) => (
                  <li key={c.id}>
                    <span className="hearing-label" title={c.matched_label ? `${c.label}: ${c.match_kind === "related_label" ? "related match" : "model label"} ${c.matched_label}` : c.label}>
                      {c.label}
                      {c.match_kind === "related_label" && <small> · related: {c.matched_label}</small>}
                    </span>
                    <Bar
                      value={c.score}
                      threshold={c.threshold}
                      strong={c.score >= c.threshold}
                    />
                    <span className="hearing-num">{c.score.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {(o.rules.name_called || o.rules.finger_snap) && (
            <dl
              className="hearing-decisions"
              aria-label="Recognition decisions"
            >
              {(
                [
                  ["name_called", "Your name"],
                  ["finger_snap", "Snap control"],
                ] as const
              ).map(([key, label]) => {
                const rule = o.rules[key];
                return rule ? (
                  <div key={key}>
                    <dt>{label}</dt>
                    <dd>
                      {RULE_REASONS[rule.reason] ??
                        rule.reason.replaceAll("_", " ")}
                    </dd>
                  </div>
                ) : null;
              })}
            </dl>
          )}
          {quiet && (
            <p className="hearing-note">
              Quiet room: labels on near-silence aren't meaningful.
            </p>
          )}
        </>
      )}
      {hearing.error && (
        <p className="hearing-note">
          Observation stream unavailable: {hearing.error}
        </p>
      )}
    </section>
  );
}
