import type { ReactElement } from "react";
import type { EventType, Tier } from "../src/lib/events";
import type { Preset } from "../src/lib/alerts";
import type { Appearance } from "../src/lib/appearance";
export interface ManaDraft {
  name: string;
  aliasesText: string;
  mode: Preset;
  rules: { key: string; tier: Tier }[];
}
export interface ManaProfile {
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
  };
}
export interface SetupChange {
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
): { tier: Tier; source: "rule" | "preset" };
export default function AwareOnboarding(props: {
  onChange?: (change: SetupChange) => void;
  onComplete?: () => void;
}): ReactElement;
