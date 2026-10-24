import type { Tier } from "./events";
export type Appearance = {
  text: "icons" | "labels";
  motion: "none" | "gentle";
  colors: Record<Tier, string>;
  direction: "unknown" | "left" | "right" | "front" | "behind";
};
export const defaultAppearance: Appearance = {
  text: "icons",
  motion: "none",
  colors: {
    0: "#ffffff",
    1: "#dcebd8",
    2: "#ffffff",
    3: "#ffe3a3",
    4: "#ffbba8",
  },
  direction: "unknown",
};
