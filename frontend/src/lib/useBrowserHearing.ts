import { useEffect, useRef, useState } from "react";
import type { SoundEvent } from "./events";
import {
  detectSounds, directedQuestion, findCall, nameEvent, questionEvent, WINDOW_SAMPLES, type PickedSound,
} from "./browserHearing";

const MODEL = "https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite";
const QUESTION_WINDOW_MS = 6000; // a question in the next phrase still counts as directed at you
const NAME_COOLDOWN_MS = 5000;

type Recognition = {
  continuous: boolean; interimResults: boolean; lang: string;
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onend: (() => void) | null; onerror: ((e: { error: string }) => void) | null;
  start(): void; stop(): void;
};
const SpeechRecognitionClass = (): (new () => Recognition) | undefined =>
  typeof window === "undefined" ? undefined
    : (window as unknown as Record<string, new () => Recognition>).SpeechRecognition
      ?? (window as unknown as Record<string, new () => Recognition>).webkitSpeechRecognition;
export const speechAvailable = () => Boolean(SpeechRecognitionClass());

export type HearingStatus = "off" | "starting" | "listening" | "error";

/** Listen with this device's microphone after an explicit click; never starts on its own. */
export function useBrowserHearing(enabled: boolean, names: string[], picked: PickedSound[], onEvent: (e: SoundEvent) => void) {
  const [status, setStatus] = useState<HearingStatus>("off");
  const [error, setError] = useState("");
  const [heard, setHeard] = useState<string[]>([]);
  const [speech, setSpeech] = useState<"off" | "on" | "unavailable">("off");
  const latest = useRef({ names, picked, onEvent });
  latest.current = { names, picked, onEvent };

  useEffect(() => {
    if (!enabled) { setStatus("off"); setHeard([]); setSpeech("off"); return; }
    let stopped = false;
    let context: AudioContext | null = null;
    let stream: MediaStream | null = null;
    let classifier: { classify(a: Float32Array, rate?: number): { classifications: { categories: { categoryName: string; score: number }[] }[] }[]; close(): void } | null = null;
    let recognition: Recognition | null = null;
    const last = new Map<string, number>();
    let lastCall = { at: -Infinity, kind: "" };
    const timers: ReturnType<typeof setTimeout>[] = [];
    setStatus("starting");
    setError("");

    (async () => {
      try {
        // Browsers only offer the microphone on https or localhost pages.
        if (!navigator.mediaDevices?.getUserMedia) throw new Error("open the https link or localhost; this address can't use the microphone");
        stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false } });
        const audio = await import("@mediapipe/tasks-audio");
        const files = await audio.FilesetResolver.forAudioTasks(`${import.meta.env?.BASE_URL ?? "/"}mediapipe/audio-wasm`);
        classifier = await audio.AudioClassifier.createFromOptions(files, { baseOptions: { modelAssetPath: MODEL }, maxResults: 25 });
        if (stopped) return;
        context = new AudioContext({ sampleRate: 16000 });
        const source = context.createMediaStreamSource(stream);
        // ScriptProcessor is deprecated but universally supported and enough for one 1 s window at a time.
        const node = context.createScriptProcessor(4096, 1, 1);
        let buffer = new Float32Array(0);
        node.onaudioprocess = (e) => {
          const input = e.inputBuffer.getChannelData(0);
          const joined = new Float32Array(buffer.length + input.length);
          joined.set(buffer); joined.set(input, buffer.length);
          buffer = joined;
          if (buffer.length < WINDOW_SAMPLES || !classifier) return;
          const chunk = buffer.slice(0, WINDOW_SAMPLES);
          buffer = buffer.slice(WINDOW_SAMPLES);
          const categories = classifier.classify(chunk, context!.sampleRate)[0]?.classifications[0]?.categories ?? [];
          const scores = new Map(categories.map((c) => [c.categoryName, c.score]));
          setHeard(categories.filter((c) => c.score >= 0.15).slice(0, 3).map((c) => c.categoryName));
          for (const event of detectSounds(scores, latest.current.picked, last, Date.now())) latest.current.onEvent(event);
        };
        source.connect(node);
        node.connect(context.destination);
        setStatus("listening");
      } catch (e) {
        if (!stopped) { setStatus("error"); setError((e as Error).message || "The microphone could not start."); }
        return;
      }

      const Recognition = SpeechRecognitionClass();
      if (!Recognition) { setSpeech("unavailable"); return; }
      recognition = new Recognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = "en-US";
      recognition.onresult = (e) => {
        for (let i = e.resultIndex; i < e.results.length; i++) {
          if (!e.results[i].isFinal) continue;
          const transcript = e.results[i][0].transcript.trim();
          const now = Date.now();
          const { names: current, onEvent: emit } = latest.current;
          const call = findCall(transcript, current);
          let after = 0;
          if (call) {
            const kind = call.alias.startsWith("warning") ? "warning" : "call";
            if (now - lastCall.at >= NAME_COOLDOWN_MS || lastCall.kind !== kind) {
              emit(nameEvent(call, now));
              after = 1500; // let the name show before the question replaces it
            }
            lastCall = { at: now, kind };
            if (kind === "warning") continue;
          }
          if (now - lastCall.at > QUESTION_WINDOW_MS) continue;
          const question = directedQuestion(transcript, current);
          if (question) timers.push(setTimeout(() => emit(questionEvent(question, transcript, Date.now())), after));
        }
      };
      // Chrome ends recognition after a pause; keep listening until the person turns it off.
      recognition.onend = () => { if (!stopped) try { recognition?.start(); } catch { /* already running */ } };
      recognition.onerror = (e) => { if (e.error === "not-allowed" || e.error === "service-not-allowed") setSpeech("unavailable"); };
      try { recognition.start(); setSpeech("on"); } catch { setSpeech("unavailable"); }
    })();

    return () => {
      stopped = true;
      timers.forEach(clearTimeout);
      recognition?.stop();
      void context?.close();
      stream?.getTracks().forEach((t) => t.stop());
      classifier?.close();
    };
  }, [enabled]);

  return { status, error, heard, speech };
}
