// Serves MediaPipe's hand-gesture runtime and model from this site so the demo works offline.
// Runs before dev/build; the model download is skipped when present and never fails the build.
import { cpSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const target = join(root, "public", "mediapipe");
const model = join(target, "gesture_recognizer.task");
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task";

mkdirSync(target, { recursive: true });
cpSync(join(root, "node_modules", "@mediapipe", "tasks-vision", "wasm"), join(target, "wasm"), { recursive: true });
if (!existsSync(model)) {
  try {
    const response = await fetch(MODEL_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    writeFileSync(model, Buffer.from(await response.arrayBuffer()));
    console.log("Gesture model saved to public/mediapipe/");
  } catch (error) {
    console.warn(`Gesture model not downloaded (${error.message}); the page will try Google's copy instead.`);
  }
}
