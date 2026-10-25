import { useEffect, useId, useRef, useState } from "react";
import catalog from "../../../audio/cue-catalog.json";
import { HOSTED, REPO_URL } from "../lib/hosted";
import {
  parseSetupSuggestions,
  type SetupSuggestion,
} from "../lib/setupSuggestions";
import type { Tier } from "../lib/events";
import { SoundIcon } from "./Cue";
const cues = new Map(catalog.cues.map((c) => [c.id, c]));
const tiers = [
  "Ignore",
  "Ambient · quiet icon",
  "Notify",
  "Attention",
  "Urgent",
];
interface ReviewRow extends SetupSuggestion {
  included: boolean;
}
export default function SetupSuggestions({
  selectedIds,
  onApply,
  connectOpen = false,
}: {
  selectedIds: string[];
  onApply: (rows: SetupSuggestion[]) => void;
  connectOpen?: boolean;
}) {
  const uid = useId();
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<"checking" | "ready" | "unavailable">(
    "checking",
  );
  const [availabilityMessage, setAvailabilityMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [rows, setRows] = useState<ReviewRow[]>([]);
  const [reviewDescription, setReviewDescription] = useState("");
  const abort = useRef<AbortController | null>(null);
  const selected = new Set(selectedIds);
  async function connect() {
    setConnecting(true);
    setError("");
    try {
      const r = await fetch("/api/setup/suggestions/key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: apiKey.trim() }),
      });
      const body = await r.json();
      if (!r.ok)
        throw new Error(body.error ?? "The key could not be configured.");
      setApiKey("");
      await check();
      setNote("Key connected for this server session only.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setConnecting(false);
    }
  }
  async function check(signal?: AbortSignal) {
    try {
      const r = await fetch("/api/setup/suggestions", {
        signal,
        cache: "no-store",
      });
      const body = await r.json();
      if (!r.ok)
        throw new Error(
          "Connect the local receiver to use Claude suggestions.",
        );
      setStatus(body.available ? "ready" : "unavailable");
      setAvailabilityMessage(
        body.available
          ? ""
          : "Claude API access is not configured yet. You can choose sounds below.",
      );
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) {
        setStatus("unavailable");
        setAvailabilityMessage((e as Error).message);
      }
    }
  }
  useEffect(() => {
    if (HOSTED) return;   // no receiver on the public demo
    const controller = new AbortController();
    void check(controller.signal);
    const timer = setInterval(() => void check(controller.signal), 5000);
    return () => {
      clearInterval(timer);
      controller.abort();
      abort.current?.abort();
    };
  }, []);
  async function suggest() {
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    setBusy(true);
    setError("");
    setNote("");
    setRows([]);
    setReviewDescription(description.trim());
    const timeout = setTimeout(() => controller.abort(), 25000);
    try {
      const r = await fetch("/api/setup/suggestions", {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: description.trim() }),
      });
      const body = await r.json();
      if (!r.ok)
        throw new Error(
          body.error ??
            "Suggestions could not be generated. Your settings were not changed.",
        );
      const result = parseSetupSuggestions(body);
      setRows(
        result.suggestions.map((row) => ({
          ...row,
          included: !selected.has(row.cue_id),
        })),
      );
      if (!result.suggestions.length)
        setNote(
          "No additional supported sounds were suggested. Try more detail, or choose sounds below.",
        );
    } catch (e) {
      setError(
        e instanceof DOMException && e.name === "AbortError"
          ? "The request timed out or was cancelled. Your settings were not changed."
          : (e as Error).message,
      );
    } finally {
      clearTimeout(timeout);
      setBusy(false);
    }
  }
  const additions = rows.filter(
    (row) => row.included && !selected.has(row.cue_id),
  );
  if (HOSTED)
    return (
      <p className="aside">
        Claude suggestions run on the laptop setup.{" "}
        <a href={REPO_URL} target="_blank" rel="noreferrer">See how to run it</a>.
      </p>
    );
  return (
    <section className="setup-suggestions" aria-labelledby={uid + "-title"}>
      <h2 id={uid + "-title"}>What matters to you?</h2>
      <p>
        Describe your day and let Claude suggest sounds. Review every choice
        before adding it.
      </p>
      <label htmlFor={uid + "-description"}>
        Your situation <span className="aside">(optional)</span>
      </label>
      <textarea
        id={uid + "-description"}
        rows={3}
        maxLength={1500}
        value={description}
        placeholder="I care for a baby and work from home. I want quiet cues unless something needs my attention."
        onChange={(e) => {
          setDescription(e.target.value);
          setRows([]);
          setError("");
          setNote("");
        }}
        disabled={busy}
      />
      <p className="aside">
        Only this description is sent to Anthropic when you ask. It is not saved
        in your profile.
      </p>
      <div className="setup-actions">
        <button
          type="button"
          className="key"
          disabled={status !== "ready" || description.trim().length < 3 || busy}
          onClick={() => void suggest()}
        >
          {busy ? "Asking Claude…" : "Suggest sounds"}
        </button>
        {busy && (
          <button
            type="button"
            className="key"
            onClick={() => abort.current?.abort()}
          >
            Cancel
          </button>
        )}
        {status === "unavailable" && (
          <button type="button" className="key" onClick={() => void check()}>
            Check connection
          </button>
        )}
      </div>
      {status !== "ready" && (
        <p className="aside" role="status">
          {status === "checking"
            ? "Checking Claude connection…"
            : availabilityMessage}
        </p>
      )}
        <details className="setup-key" open={connectOpen}>
          <summary>Connect Claude securely</summary>
          {status === "ready" && <p role="status">Claude is connected for this session. You can replace the key below.</p>}
          <p className="aside">
            Enter an Anthropic API key. It stays in the local server's memory,
            is never saved to disk or browser storage, and clears when the
            server stops. A Claude app subscription does not include API credit.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void connect();
            }}
          >
            <label htmlFor={uid + "-key"}>Anthropic API key</label>
            <input
              id={uid + "-key"}
              type="password"
              autoComplete="off"
              spellCheck={false}
              value={apiKey}
              maxLength={512}
              onChange={(e) => setApiKey(e.target.value)}
              disabled={connecting}
            />
            <button
              type="submit"
              className="key"
              disabled={connecting || !apiKey.trim()}
            >
              {connecting ? "Connecting…" : "Connect for this session"}
            </button>
          </form>
        </details>
      {error && <p role="alert">{error}</p>}
      {rows.length > 0 && (
        <div className="setup-review">
          <h3>Review suggested sounds</h3>
          <p className="aside">
            Nothing has been changed. Your existing choices will be kept.
          </p>
          <ul>
            {rows.map((row, index) => {
              const cue = cues.get(row.cue_id)!;
              const exists = selected.has(row.cue_id);
              return (
                <li key={row.cue_id}>
                  <label className="setup-review-choice">
                    <input
                      type="checkbox"
                      checked={!exists && row.included}
                      disabled={exists}
                      onChange={(e) =>
                        setRows((current) =>
                          current.map((r, i) =>
                            i === index
                              ? { ...r, included: e.target.checked }
                              : r,
                          ),
                        )
                      }
                    />
                    <SoundIcon type="custom" iconId={cue.icon_id} size={28} />
                    <span>
                      <strong>{cue.label}</strong>
                      <small>
                        {exists
                          ? "Already set · keeping your choice"
                          : row.reason}
                      </small>
                    </span>
                  </label>
                  {!exists && (
                    <select
                      aria-label={"Suggested priority for " + cue.label}
                      value={row.tier}
                      onChange={(e) =>
                        setRows((current) =>
                          current.map((r, i) =>
                            i === index
                              ? { ...r, tier: Number(e.target.value) as Tier }
                              : r,
                          ),
                        )
                      }
                    >
                      {tiers.map((label, tier) => (
                        <option value={tier} key={tier}>
                          {label}
                        </option>
                      ))}
                    </select>
                  )}
                </li>
              );
            })}
          </ul>
          <button
            type="button"
            className="key"
            disabled={
              !additions.length || reviewDescription !== description.trim()
            }
            onClick={() => {
              onApply(
                additions.map(({ cue_id, tier, reason }) => ({
                  cue_id,
                  tier,
                  reason,
                })),
              );
              setRows([]);
              setDescription("");
              setNote("Selected suggestions added. You can change them below.");
            }}
          >
            Add {additions.length} selected{" "}
            {additions.length === 1 ? "sound" : "sounds"}
          </button>
        </div>
      )}
      {note && <p role="status">{note}</p>}
    </section>
  );
}
