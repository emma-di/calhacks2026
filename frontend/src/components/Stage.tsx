import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Camera, CameraOff } from "lucide-react";
import Oled from "./Oled";
import { useThumbsUp } from "../lib/gesture";
import type { SoundEvent } from "../lib/events";

// The camera only ever starts from a click, stays in this tab and is never recorded or sent anywhere.
function useCamera() {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const current = useRef<MediaStream | null>(null);
  const generation = useRef(0);
  const stop = useCallback(() => {
    generation.current++;
    current.current?.getTracks().forEach((track) => track.stop());
    current.current = null;
    setStream(null);
  }, []);
  const start = useCallback(
    async (id?: string) => {
      const version = ++generation.current;
      setError(null);
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("This browser cannot open a camera here.");
        return;
      }
      try {
        const next = await navigator.mediaDevices.getUserMedia({
          video: id
            ? { deviceId: { exact: id } }
            : { facingMode: "environment" },
          audio: false,
        });
        if (version !== generation.current) {
          next.getTracks().forEach((track) => track.stop());
          return;
        }
        current.current?.getTracks().forEach((track) => track.stop());
        current.current = next;
        setStream(next);
        setDeviceId(
          next.getVideoTracks()[0]?.getSettings().deviceId ?? id ?? "",
        );
        next.getVideoTracks().forEach((track) =>
          track.addEventListener(
            "ended",
            () => {
              if (current.current === next) {
                stop();
                setError(
                  "Camera disconnected. Reconnect it, then choose Use POV camera.",
                );
              }
            },
            { once: true },
          ),
        );
        // Device enumeration failure must not discard a successfully opened camera.
        try {
          const all = await navigator.mediaDevices.enumerateDevices();
          if (version === generation.current)
            setDevices(all.filter((d) => d.kind === "videoinput"));
        } catch {
          /* The selected camera can still play. */
        }
      } catch (e) {
        if (version !== generation.current) return;
        const name = (e as DOMException).name;
        setError(
          name === "NotAllowedError"
            ? "Camera access is blocked. Allow it in this site's settings, then try again."
            : name === "NotFoundError" || name === "OverconstrainedError"
              ? "No camera found."
              : "The camera could not start. Another app may be using it.",
        );
      }
    },
    [stop],
  );
  useEffect(
    () => () => {
      generation.current++;
      current.current?.getTracks().forEach((track) => track.stop());
      current.current = null;
    },
    [],
  );
  return { stream, devices, deviceId, error, start, stop };
}

// Simulated wearer view: an optional demo camera backdrop, not a camera on the glasses.
// so the live view and the panel can never disagree.
export default function Stage({
  event,
  labels,
  direction,
  caption,
  large = false,
  motion = "none",
  accent,
  onGesture,
  children,
}: {
  event: SoundEvent | null;
  labels: boolean;
  direction: string | null;
  caption: string;
  large?: boolean;
  motion?: "none" | "gentle";
  accent?: string;
  onGesture?: (eventId: string) => void;
  children?: ReactNode;
}) {
  const camera = useCamera();
  const [gesturesEnabled, setGesturesEnabled] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (video.current) video.current.srcObject = camera.stream;
  }, [camera.stream]);
  const cueId =
    event && event.type !== ("resolved" as string) ? event.event_id : null;
  const gesture = useThumbsUp(
    video,
    Boolean(camera.stream && gesturesEnabled && onGesture),
    (eventId) => onGesture?.(eventId),
    cueId,
  );
  const gestureText = {
    off: "",
    loading: "Loading gesture model…",
    watching: cueId
      ? "Hold thumbs-up for ½ second to dismiss"
      : "Gestures ready · waiting for an alert",
    hand: "Hand seen · hold thumbs-up",
    holding: "Hold thumbs-up…",
    release: "Lower your hand to re-arm gestures",
    error: "Gestures unavailable · use Dismiss",
  };

  return (
    <section
      className={`stage ${large ? "stage-large" : ""}`}
      aria-label="Wearer's view"
    >
      {camera.stream && (
        <video
          ref={video}
          className="stage-video"
          autoPlay
          muted
          playsInline
          aria-hidden="true"
        />
      )}
      <div className="stage-bar">
        <span className="stage-caption">
          {camera.stream ? `Demo POV camera · ${caption}` : caption}
        </span>
        <span className="stage-tools">
          {camera.stream && onGesture && (
            <button
              className="stage-button"
              aria-pressed={gesturesEnabled}
              onClick={() => setGesturesEnabled((value) => !value)}
            >
              {gesturesEnabled ? "Gestures on" : "Enable thumbs-up"}
            </button>
          )}
          {camera.stream && camera.devices.length > 1 && (
            <select
              aria-label="Camera"
              value={camera.deviceId}
              onChange={(e) => void camera.start(e.target.value)}
            >
              {camera.devices.map((d, i) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label || `Camera ${i + 1}`}
                </option>
              ))}
            </select>
          )}
          <button
            className="stage-button"
            onClick={() =>
              camera.stream ? camera.stop() : void camera.start()
            }
            aria-pressed={Boolean(camera.stream)}
          >
            {camera.stream ? <CameraOff size={15} /> : <Camera size={15} />}
            {camera.stream ? "Stop camera" : "Use POV camera"}
          </button>
        </span>
      </div>
      {gesture !== "off" && (
        <p className={`gesture-demo-status is-${gesture}`} role="status">
          Demo camera · {gestureText[gesture]}
        </p>
      )}
      {camera.error && (
        <p className="stage-error" role="alert">
          {camera.error}
        </p>
      )}
      <div
        key={event?.event_id ?? "idle"}
        style={
          event && accent
            ? { filter: `drop-shadow(0 0 5px ${accent})` }
            : undefined
        }
        className={`lens-frame ${event ? "is-lit" : ""} ${event?.priority_tier === 4 ? "is-urgent" : ""} ${motion === "gentle" ? "gentle-cue" : ""}`}
      >
        <Oled event={event} labels={labels} direction={direction} lens />
      </div>
      {!event && <p className="lens-idle">Quiet</p>}
      {children}
    </section>
  );
}
