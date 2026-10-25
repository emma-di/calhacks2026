import type { ManaProfile } from './AwareOnboarding.jsx';
type Request = (path: string, body?: unknown, signal?: AbortSignal, method?: "GET" | "PUT") => Promise<unknown>;
export function createAwareReceiverAdapter(request: Request): {
  readProfile(signal?: AbortSignal): Promise<ManaProfile>;
  saveEdits(patch: Record<string, unknown>, signal?: AbortSignal): Promise<ManaProfile>;
};
