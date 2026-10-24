import { GestureHold } from "./gesture-hold";
import { useEffect, useRef, useState, type RefObject } from "react";

// Thumbs-up to dismiss, seen by whichever camera the lens shows (the glasses' camera when it appears
// as a webcam, or the laptop's). Runs MediaPipe's hand-gesture model in this tab; nothing leaves it.
const FRAME_MS = 66;
const LOCAL_MODEL = "/mediapipe/gesture_recognizer.task";
const REMOTE_MODEL =
  "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task";

export type GestureStatus =
  "off" | "loading" | "watching" | "hand" | "holding" | "error";

export function useThumbsUp(
  video: RefObject<HTMLVideoElement | null>,
  active: boolean,
  onGesture: () => void,
) {
  const [status, setStatus] = useState<GestureStatus>("off");
  const callback = useRef(onGesture);
  callback.current = onGesture;

  useEffect(() => {
    if (!active) {
      setStatus("off");
      return;
    }
    let cancelled = false;
    let frame = 0;
    let recognizer: { recognizeForVideo: Function; close: () => void } | null =
      null;
    setStatus("loading");
    (async () => {
      try {
        const vision = await import("@mediapipe/tasks-vision");
        const files =
          await vision.FilesetResolver.forVisionTasks("/mediapipe/wasm");
        const make = (modelAssetPath: string) =>
          vision.GestureRecognizer.createFromOptions(files, {
            baseOptions: { modelAssetPath },
            runningMode: "VIDEO",
            numHands: 1,
          });
        recognizer = await make(LOCAL_MODEL).catch(() => make(REMOTE_MODEL));
        if (cancelled) return recognizer.close();
        setStatus("watching");
        let last = 0;
        const hold = new GestureHold();
        const loop = (now: number) => {
          frame = requestAnimationFrame(loop);
          const element = video.current;
          if (
            !recognizer ||
            !element ||
            element.readyState < 2 ||
            now - last < FRAME_MS
          )
            return;
          last = now;
          let result;
          try {
            result = recognizer.recognizeForVideo(element, now);
          } catch {
            cancelAnimationFrame(frame);
            setStatus("error");
            return;
          }
          const top = result.gestures?.[0]?.[0];
          const thumb = top?.categoryName === "Thumb_Up" && top.score > 0.6;
          const fire = hold.update(thumb, now);
          if (!thumb) {
            setStatus(result.landmarks?.length ? "hand" : "watching");
            return;
          }
          setStatus("holding");
          if (fire) callback.current();
        };
        frame = requestAnimationFrame(loop);
      } catch {
        if (!cancelled) setStatus("error");
      }
    })();
    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
      recognizer?.close();
    };
  }, [active, video]);

  return status;
}
