import type { ReactElement } from "react";
import type { EventType, Tier } from "../src/lib/events";
import type { Preset } from "../src/lib/alerts";
import type { Appearance } from "../src/lib/appearance";
export interface ManaDraft {
  name: string;
  name_enabled?: boolean;
  aliasesText: string;
  mode: Preset;
  rules: { key: string; tier: Tier }[];
  custom_rules?: CustomSound[];
  category_rules?: Record<string, Tier>;
}
export interface CustomSound {
  id: string;
  label: string;
  tier: Tier;
  status: "pending" | "recognized";
  cue_id?: string;
  icon_id?: string;
  model_labels?: string[];
  icon?: string;
  threshold?: number;
}
export interface CuratedCue {
  id: string; label: string; aliases: string[]; model_labels: string[];
  icon_id: string; default_tier: Tier; category: string;
  event_type: string; experimental: boolean; threshold: number;
}
export function searchCuratedSounds(query: string): CuratedCue[];
export function createCueRule(cueId: string, tier: Tier, id: string): CustomSound | null;
export function applyCuratedRule(draft: unknown, cueId: string, tier: Tier, id: string): ManaDraft;
export function sanitizeCustomSounds(raw: unknown): CustomSound[];
export interface ManaProfile {
  display?: { labels: boolean };
  custom_sound_requests?: CustomSound[];
  schema_version: 1;
  profile_id: string;
  revision: number;
  display_name: string;
  name_detection: {
    enabled: boolean;
    primary_name: string;
    aliases: string[];
    language: string;
  };
  notification_preferences: {
    mode: Preset;
    event_tiers: Partial<Record<EventType, Tier>>;
    category_tiers?: Partial<
      Record<"home" | "animals" | "people" | "safety", Tier>
    >;
  };
}
export interface SetupChange {
  editRevision: number;
  profile: ManaProfile;
  display: {
    labels: boolean;
    motion: "off" | "pulse";
    colors: Record<1 | 2 | 3 | 4, string>;
  };
  direction: Appearance["direction"];
}
export const AWARE_PRESET_DEFAULTS: Record<
  Preset,
  Partial<Record<EventType, Tier>>
>;
export const AWARE_EMPTY_DRAFT: ManaDraft;
export function buildAwareProfile(draft: unknown): ManaProfile;
export function setAwareRule(
  draft: unknown,
  key: string,
  tier: number,
): ManaDraft;
export function removeAwareRule(draft: unknown, key: string): ManaDraft;
export function resolveAwareTier(
  draft: unknown,
  key: string,
): { tier: Tier; source: "rule" | "category" | "preset" };
export default function AwareOnboarding(props: {
  onChange?: (change: SetupChange) => void;
  onComplete?: () => void;
  theme?: "light" | "dark";
  receiverProfile?: ManaProfile | null;
}): ReactElement;
