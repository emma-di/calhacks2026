import { piLevelFraction, usePiMicrophoneLevels } from "../lib/piLevels";

/** Real I²S channel levels, independent from the Mac recognizer's observation stream. */
export default function PiMicrophoneLevels() {
  const input = usePiMicrophoneLevels();
  const live = input.status === "live";
  const status = {
    pending: "Connecting to Pi audio…",
    offline: "Pi audio offline",
    stale: "Pi audio feed stopped",
    live: "Pi audio live · stereo · 48 kHz",
  }[input.status];
  return (
    <section className="hearing pi-microphones" aria-labelledby="pi-microphones-heading">
      <header className="hearing-head">
        <h2 id="pi-microphones-heading">Pi microphones</h2>
        <span className={`dot ${live ? "" : "is-off"}`} aria-hidden="true" />
        <span className="hearing-status" role="status">{status}</span>
      </header>
      <div className="pi-microphone-channels">
        {["Left channel", "Right channel"].map((label, index) => {
          const level = input.levels?.[index];
          return (
            <div className="pi-microphone-channel" key={label}>
              <div className="pi-microphone-values">
                <span>{label}</span>
                <span className="hearing-num">{level ? `${level.rms_dbfs.toFixed(1)} dBFS` : "— dBFS"}</span>
              </div>
              <div className={`pi-microphone-track ${live ? "" : "is-off"}`} role={level ? "meter" : "img"}
                aria-label={`${label} RMS level`}
                {...(level ? { "aria-valuemin": -60, "aria-valuemax": 0, "aria-valuenow": Math.max(-60, level.rms_dbfs) } : {})}
                aria-valuetext={level ? `${level.rms_dbfs.toFixed(1)} dBFS RMS, peak ${level.peak_dbfs.toFixed(1)} dBFS` : "No current audio data"}>
                <span className="pi-microphone-fill" style={{ transform: `scaleX(${level ? piLevelFraction(level.rms_dbfs) : 0})` }} />
                {level && <span className="pi-microphone-peak" style={{ left: `${piLevelFraction(level.peak_dbfs) * 100}%` }} />}
              </div>
              <p className="pi-microphone-detail">
                {level ? `Peak ${level.peak_dbfs.toFixed(1)} dBFS` : "Waiting for channel data"}
                {level && level.clip_fraction > 0 && <span className="pi-microphone-clipping"> · Clipping {(level.clip_fraction * 100).toFixed(1)}%</span>}
              </p>
            </div>
          );
        })}
      </div>
      <p className="aside">Levels only · sound recognition still uses the Mac microphone.</p>
      <p className="aside">Left/right are stereo I²S slots; physical sides are not confirmed. This is not a spatial estimate.</p>
      {input.error && !live && <p className="pi-microphone-error">{input.error}</p>}
    </section>
  );
}
