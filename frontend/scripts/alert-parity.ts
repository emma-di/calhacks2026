// Companion side of scripts/verify_alert_parity.py; no browser, server, camera or microphone.
import { readFileSync } from "node:fs";
import { AlertEngine } from "../src/lib/alerts.ts";
const actions = JSON.parse(readFileSync(0, "utf8"));
const engine = new AlertEngine();
const output = actions.map((a: any) => {
  if (a.event) engine.add(a.event, a.at);
  else if (a.controls) engine.setControls(a.at, a.controls);
  else if ("dismiss" in a) engine.dismiss(a.at, a.dismiss);
  else engine.tick(a.at);
  const s = engine.snapshot(a.at);
  return {
    active: s.active ? [s.active.event_id, s.active.priority_tier] : null,
    remaining: s.remaining_ms,
    sequence: s.state_sequence,
    direction: s.direction,
    confirm: s.confirm,
    queue: s.queue,
    paused: s.paused,
    focus: s.focus_mode,
    last: s.decisions.at(-1)
      ? [s.decisions.at(-1)!.event_id, s.decisions.at(-1)!.reason]
      : null,
  };
});
process.stdout.write(JSON.stringify(output));
