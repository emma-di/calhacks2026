import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Camera, CameraOff } from "lucide-react";
import Oled from "./Oled";
import { useThumbsUp, type GestureStatus } from "../lib/gesture";
import type { SoundEvent } from "../lib/events";

// The camera only ever starts from a click, stays in this tab and is never recorded or sent anywhere.
function useCamera() {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const stop = useCallback(() => {
    setStream((current) => {
      current?.getTracks().forEach((track) => track.stop());
      return null;
    });
  }, []);
  const start = useCallback(
    async (id?: string) => {
      setError(null);
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("This browser cannot open a camera here.");
        return;
      }
      try {
        const next = await navigator.mediaDevices.getUserMedia({
          video: id ? { deviceId: { exact: id } } : { facingMode: "environment" },
          audio: false,
        });
        stop();
        setStream(next);
        setDeviceId(next.getVideoTracks()[0]?.getSettings().deviceId ?? id ?? "");
        const all = await navigator.mediaDevices.enumerateDevices();
        setDevices(all.filter((d) => d.kind === "videoinput"));
      } catch (e) {
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
  useEffect(() => stop, [stop]);
  return { stream, devices, deviceId, error, start, stop };
}

const gestureText: Record<GestureStatus, string> = {
  off: "",
  loading: "Loading hand tracking…",
  watching: "Thumbs up to dismiss",
  hand: "Hand seen · thumbs up to dismiss",
  holding: "Thumbs up…",
  error: "Hand tracking unavailable",
};

// The wearer's view: the room (camera) or darkness, with the glasses' own 128x64 frame floating in it,
// so the live view and the panel can never disagree.
export default function Stage({
  event,
  labels,
  direction,
  caption,
  large = false,
  motion = "none",
  onGesture,
  children,
}: {
  event: SoundEvent | null;
  labels: boolean;
  direction: string | null;
  caption: string;
  large?: boolean;
  motion?: "none" | "gentle";
  onGesture?: () => void;
  children?: ReactNode;
}) {
  const camera = useCamera();
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (video.current) video.current.srcObject = camera.stream;
  }, [camera.stream]);
  const gesture = useThumbsUp(video, Boolean(camera.stream && onGesture), () => onGesture?.());
  return (
    <section className={`stage ${large ? "stage-large" : ""}`} aria-label="Wearer's view">
      {camera.stream && (
        <video ref={video} className="stage-video" autoPlay muted playsInline aria-hidden="true" />
      )}
      <div className="stage-bar">
        <span className="stage-caption">{caption}</span>
        {gesture !== "off" && (
          <span className={`gesture-status is-${gesture}`} role="status">
            {gestureText[gesture]}
          </span>
        )}
        <span className="stage-tools">
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
            onClick={() => (camera.stream ? camera.stop() : void camera.start())}
            aria-pressed={Boolean(camera.stream)}
          >
            {camera.stream ? <CameraOff size={15} /> : <Camera size={15} />}
            {camera.stream ? "Stop camera" : "Show my room"}
          </button>
        </span>
      </div>
      {camera.error && (
        <p className="stage-error" role="alert">
          {camera.error}
        </p>
      )}
      <div
        key={event?.event_id ?? "idle"}
        className={`lens-frame ${event ? "is-lit" : ""} ${event?.priority_tier === 4 ? "is-urgent" : ""} ${motion === "gentle" ? "gentle-cue" : ""}`}
      >
        <Oled event={event} labels={labels} direction={direction} lens />
      </div>
      {!event && <p className="lens-idle">Quiet</p>}
      {children}
    </section>
  );
}
