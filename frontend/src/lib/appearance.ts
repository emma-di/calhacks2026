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
    0: "#f4f2ea",
    1: "#b4b2aa",
    2: "#f4f2ea",
    3: "#f4f2ea",
    4: "#df443d",
  },
  direction: "unknown",
};
