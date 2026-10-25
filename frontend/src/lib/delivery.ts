import type { SoundEvent } from "./events";

// Session routing and an event's provenance are different: a camera gesture may still be simulated.
export async function deliverEvent(
  mode: "browser" | "receiver",
  event: SoundEvent,
  addLocal: (event: SoundEvent) => void,
  post: (path: string, body: unknown) => Promise<unknown>,
) {
  if (mode === "browser") {
    addLocal(event);
    return;
  }
  await post("/events", { ...event, confidence: null });
}
