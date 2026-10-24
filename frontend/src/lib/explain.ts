import { soundCatalog, tierNames, type Tier } from "./events";

export interface Explainable {
  event_id: string;
  type: string;
  priority_tier: Tier;
  reason: string;
  active_type?: string | null;
  label?: string;
  active_label?: string | null;
  direction?: string;
  gesture?: string;
}

const gestureName = (gesture?: string) => (gesture === "finger_snap" ? "Snap" : "Thumbs up");
// A taught custom sound is named by the user ("Front doorbell"); built-in sounds use the catalog label.
const name = (type?: string | null, label?: string | null) =>
  (type === "custom" && label) ||
  (soundCatalog.find((s) => s.type === type)?.label ?? type ?? "another cue");

// One sentence per backend decision, written for someone watching the demo, not for a log reader.
export function explain(d: Explainable): string {
  const sound = name(d.type, d.label);
  const other = name(d.active_type, d.active_label);
  const tier = tierNames[d.priority_tier];
  switch (d.reason) {
    case "displayed":
      return `${sound} shown as ${tier}.`;
    case "interrupted":
      return `${sound} (${tier}) took over from ${other}.`;
    case "queued":
      return `${sound} is waiting while ${other} is showing.`;
    case "resumed_from_queue":
      return `${sound} came back once the screen was free.`;
    case "expired_in_queue":
      return `${sound} waited too long and was dropped, so it never shows late.`;
    case "dropped_queue_full":
      return `${sound} was dropped to keep the waiting list short.`;
    case "merged_repeat":
      return `${sound} again. Same cue kept, not restarted.`;
    case "acknowledged_repeat":
      return `${sound} still going. Already dismissed, so it stays quiet.`;
    case "expired":
      return `${sound} cleared on its own.`;
    case "resolved_looked":
      return `You looked ${d.direction ?? "toward it"}, so ${sound} is resolved.`;
    case "gesture_ignored":
      return `${gestureName(d.gesture)} seen, but nothing is showing.`;
    case "gesture_waiting":
      return `${gestureName(d.gesture)} seen. Once more to dismiss.`;
    case "dismissed_gesture":
      return `${gestureName(d.gesture)}. ${sound} dismissed.`;
    case "dismissed":
      return `${sound} dismissed. Repeats stay quiet for 15 seconds.`;
    case "duplicate":
      return `${sound} arrived twice with the same ID and was counted once.`;
    case "paused":
      return `${sound} heard while paused. Nothing is shown.`;
    case "ignored_tier_zero":
      return `${sound} is set to Ignore.`;
    case "suppressed_lower_priority":
      return `${sound} skipped: ${other} matters more right now.`;
    case "held_work_mode":
      return `${sound} held back by Work mode.`;
    case "held_dnd_mode":
      return `${sound} held back by Do not disturb.`;
    default:
      return `${sound}: ${d.reason.replaceAll("_", " ")}.`;
  }
}

// Short status for the log's outcome column.
export function outcome(reason: string): string {
  return (
    {
      displayed: "Shown",
      interrupted: "Shown, took over",
      resumed_from_queue: "Shown after waiting",
      queued: "Waiting",
      expired_in_queue: "Dropped, too late",
      dropped_queue_full: "Dropped",
      merged_repeat: "Repeat, merged",
      acknowledged_repeat: "Repeat, already dismissed",
      dismissed: "Dismissed",
      dismissed_gesture: "Dismissed, gesture",
      gesture_ignored: "Gesture, nothing showing",
      gesture_waiting: "Gesture, waiting for another",
      expired: "Cleared",
      resolved_looked: "Resolved, looked",
      duplicate: "Duplicate",
      paused: "Paused",
      ignored_tier_zero: "Ignored",
      suppressed_lower_priority: "Skipped",
      held_work_mode: "Held, Work",
      held_dnd_mode: "Held, Do not disturb",
    } as Record<string, string>
  )[reason] ?? reason.replaceAll("_", " ");
}
