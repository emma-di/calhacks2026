import {
  Bell,
  DoorOpen,
  Dog,
  Flame,
  MessageCircle,
  Radio,
  UserRound,
  Clock3,
  type LucideIcon,
} from "lucide-react";
import { tierNames, type EventType, type SoundEvent } from "../lib/events";
import type { Appearance } from "../lib/appearance";
import { cuePresentation } from "../lib/presentation";
const icons: Record<EventType, LucideIcon> = {
  knock: DoorOpen,
  bell: Bell,
  bicycle_bell: Bell,
  dog_bark: Dog,
  name_called: UserRound,
  smoke_alarm: Flame,
  conversation: MessageCircle,
  siren: Radio,
  alarm_clock: Clock3,
};
export function SoundIcon({
  type,
  size = 22,
}: {
  type: EventType;
  size?: number;
}) {
  const Icon = icons[type];
  return <Icon size={size} strokeWidth={1.7} aria-hidden="true" />;
}
export default function Cue({
  event,
  appearance,
  direction,
}: {
  event: SoundEvent | null;
  appearance: Appearance;
  direction: Appearance["direction"];
}) {
  const presentation = cuePresentation(event, appearance, direction);
  const visible = presentation && event;
  const text = presentation?.label;
  return (
    <div
      className={`cue-region edge-${visible ? direction : "unknown"}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {visible ? (
        <div
          key={event.event_id}
          className={`cue tier-${event.priority_tier} ${text ? "" : "icon-only"} ${appearance.motion === "gentle" ? "gentle-cue" : ""}`}
          role="group"
          aria-label={`${tierNames[event.priority_tier]}: ${event.label}`}
          style={{
            color: appearance.colors[event.priority_tier],
            borderColor: appearance.colors[event.priority_tier],
          }}
        >
          <span className="cue-symbol">
            <SoundIcon type={event.type} size={32} />
          </span>
          {text && <strong>{event.label}</strong>}
        </div>
      ) : (
        <div className="cue-idle">
          <span className="idle-orbit" />
          <span>Quiet. Play a sound to see its cue here.</span>
        </div>
      )}
    </div>
  );
}
