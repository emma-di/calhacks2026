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
  return <Icon size={size} strokeWidth={1.6} aria-hidden="true" />;
}
export default function Cue({
  event,
  oled = false,
}: {
  event: SoundEvent | null;
  oled?: boolean;
}) {
  const visible = event && event.priority_tier > 0;
  return (
    <div
      className={`cue-region ${oled ? "oled-cue" : ""}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {visible ? (
        <div key={event.event_id} className={`cue tier-${event.priority_tier}`}>
          <span className="cue-symbol">
            <SoundIcon type={event.type} size={oled ? 25 : 32} />
          </span>
          <div>
            <span className="cue-eyebrow">
              {tierNames[event.priority_tier]}
            </span>
            <strong>{event.label}</strong>
          </div>
          {!oled && (
            <span className="cue-tail" aria-hidden="true">
              ●
            </span>
          )}
        </div>
      ) : (
        <div className="cue-idle">
          <span className="idle-orbit" />
          <span>
            {oled ? "No active cue" : "A little quiet. A little clarity."}
          </span>
        </div>
      )}
    </div>
  );
}
