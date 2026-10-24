import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, CameraOff } from "lucide-react";
import Cue from "./Cue";
import type { SoundEvent } from "../lib/events";
import type { Appearance } from "../lib/appearance";

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

export default function Stage({
  event,
  appearance,
  direction,
  caption,
  large = false,
}: {
  event: SoundEvent | null;
  appearance: Appearance;
  direction: Appearance["direction"];
  caption: string;
  large?: boolean;
}) {
  const camera = useCamera();
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (video.current) video.current.srcObject = camera.stream;
  }, [camera.stream]);
  return (
    <section className={`stage ${large ? "stage-large" : ""}`} aria-label="Wearer's view">
      {camera.stream && (
        <video ref={video} className="stage-video" autoPlay muted playsInline aria-hidden="true" />
      )}
      <div className="stage-bar">
        <span className="stage-caption">{caption}</span>
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
      <Cue event={event} appearance={appearance} direction={direction} />
    </section>
  );
}
