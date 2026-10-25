import catalog from "../../../audio/cue-catalog.json";
import type { Tier } from "./events";
export interface SetupSuggestion {
  cue_id: string;
  tier: Tier;
  reason: string;
}
export interface SuggestionResponse {
  suggestions: SetupSuggestion[];
  provider: string;
  model: string;
}
const allowed = new Set(
  catalog.cues
    .filter((c) => !c.experimental && c.event_type !== "name_called")
    .map((c) => c.id),
);
export function parseSetupSuggestions(input: unknown): SuggestionResponse {
  const value = input as Partial<SuggestionResponse> | null;
  if (
    !value ||
    !Array.isArray(value.suggestions) ||
    value.suggestions.length > 8
  )
    throw new Error(
      "Claude returned an invalid sound list. Nothing was applied.",
    );
  const seen = new Set<string>();
  for (const row of value.suggestions) {
    if (
      !row ||
      !allowed.has(row.cue_id) ||
      seen.has(row.cue_id) ||
      !Number.isInteger(row.tier) ||
      row.tier < 0 ||
      row.tier > 4 ||
      typeof row.reason !== "string" ||
      !row.reason.trim() ||
      row.reason.length > 240
    )
      throw new Error(
        "Claude returned an unsupported suggestion. Nothing was applied.",
      );
    seen.add(row.cue_id);
  }
  return {
    suggestions: value.suggestions,
    provider: typeof value.provider === "string" ? value.provider : "Anthropic",
    model: typeof value.model === "string" ? value.model : "",
  };
}
