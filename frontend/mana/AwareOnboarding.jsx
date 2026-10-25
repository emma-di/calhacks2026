// Aware onboarding and preferences.
// Mana source of truth: file-system/apps/Aware/app/code. A standalone copy is exported as AwareOnboarding.jsx.
// Plain React with inline styles; no Mana APIs are required (theme support is used only when present).
import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import modelCatalog from "../../audio/sound-catalog.json";
import cueCatalog from "../../audio/cue-catalog.json";
import alertPolicy from "../../audio/alert-policy.json";
import Oled from "../src/components/Oled";
import { makeMock } from "../src/lib/events";
import { directionBucket } from "../src/lib/alerts";

// --- profile logic ---
export const AWARE_TIERS = [
  { value: 0, label: "Ignore", hint: "No cue." },
  { value: 1, label: "Ambient", hint: "Faint, glanceable cue." },
  { value: 2, label: "Notify", hint: "Standard cue." },
  { value: 3, label: "Attention", hint: "Prominent cue." },
  { value: 4, label: "Urgent", hint: "Strongest cue, with short text." },
];

// Sounds the classifier supports. Search terms only point at these; they never create new labels.
export const AWARE_EVENTS = [
  {
    key: "knock",
    label: "Knock",
    cue: "Knock",
    terms: ["knock", "knocking", "door knock", "tapping"],
  },
  {
    key: "bell",
    label: "Bell or chime",
    cue: "Bell or chime",
    terms: ["bell", "chime", "ding"],
    hint: "Generic bell/chime. Select Doorbell from the model catalog for a doorbell-specific rule.",
  },
  {
    key: "dog_bark",
    label: "Dog barking",
    cue: "Dog barking",
    terms: ["dog", "bark", "barking", "woof"],
  },
  {
    key: "name_called",
    label: "Name called",
    cue: "Name called",
    terms: ["name", "my name", "called", "calling"],
    hint: "Uses the speech recognizer and the name under Name (optional).",
  },
  {
    key: "smoke_alarm",
    label: "Fire / smoke alarm",
    cue: "Fire / smoke alarm",
    terms: ["smoke", "smoke alarm", "smoke detector", "fire alarm", "fire"],
  },
  {
    key: "alarm_clock",
    label: "Alarm clock",
    cue: "Alarm clock",
    terms: ["alarm clock", "alarm", "wake", "wake up", "clock"],
  },
  {
    key: "siren",
    label: "Siren",
    cue: "Siren",
    terms: [
      "siren",
      "ambulance",
      "police",
      "fire truck",
      "fire engine",
      "emergency vehicle",
    ],
  },
];

export const AWARE_PRESETS = [
  {
    key: "gentle",
    label: "Gentle",
    hint: "Fewer interruptions. Safety sounds still come through.",
  },
  { key: "balanced", label: "Balanced", hint: "Recommended starting point." },
  {
    key: "active",
    label: "Active",
    hint: "More prominent cues for everyday sounds.",
  },
];

// Balanced is the agreed mapping. Gentle and Active are provisional and only drive the preview; they are never exported.
export const AWARE_PRESET_DEFAULTS = {
  balanced: {
    dog_bark: 1,
    knock: 2,
    bell: 2,
    name_called: 3,
    smoke_alarm: 4,
    alarm_clock: 2,
    siren: 3,
  },
  gentle: {
    dog_bark: 1,
    knock: 1,
    bell: 1,
    name_called: 2,
    smoke_alarm: 4,
    alarm_clock: 2,
    siren: 3,
  },
  active: {
    dog_bark: 2,
    knock: 3,
    bell: 3,
    name_called: 3,
    smoke_alarm: 4,
    alarm_clock: 3,
    siren: 4,
  },
};

export const AWARE_EMPTY_DRAFT = {
  name: "",
  aliasesText: "",
  mode: "balanced",
  rules: [],
};

export function isAwareTier(v) {
  return Number.isInteger(v) && v >= 0 && v <= 4;
}
function awareEvent(key) {
  return AWARE_EVENTS.find((e) => e.key === key) || null;
}
function awareTierLabel(v) {
  const t = AWARE_TIERS.find((x) => x.value === v);
  return t ? t.label : String(v);
}

function parseAwareAliases(text, primary) {
  const seen = new Set();
  const primaryKey = (primary || "").trim().toLowerCase();
  if (primaryKey) seen.add(primaryKey);
  const out = [];
  String(text || "")
    .split(/[,\n]/)
    .forEach((part) => {
      const alias = part.trim().replace(/\s+/g, " ");
      const k = alias.toLowerCase();
      if (alias && !seen.has(k)) {
        seen.add(k);
        out.push(alias);
      }
    });
  return out;
}

const catalogLabels = new Map(modelCatalog.sounds.map((sound) => [sound.label, sound]));

const cuesById = new Map(cueCatalog.cues.map((cue) => [cue.id, cue]));
const curatedModelLabels = new Set(cueCatalog.cues.flatMap((cue) => cue.model_labels));
const normalizeSearch = (text) => String(text).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

export function searchCuratedSounds(query) {
  const q = normalizeSearch(query);
  if (!q) return [];
  const words = q.split(" ");
  return cueCatalog.cues.filter((cue) => {
    const text = normalizeSearch([cue.label, ...cue.aliases, ...cue.model_labels].join(" "));
    return words.every((word) => text.includes(word));
  }).sort((a, b) => Number(normalizeSearch(b.label) === q) - Number(normalizeSearch(a.label) === q));
}

export function createCueRule(cueId, tier, id) {
  const cue = cuesById.get(cueId);
  if (!cue || cue.experimental || cue.event_type !== "custom" || !isAwareTier(tier)) return null;
  return {
    id, cue_id: cue.id, label: cue.label, tier, status: "recognized",
    model_labels: [...cue.model_labels], icon_id: cue.icon_id, icon: cue.icon_id, threshold: cue.threshold,
  };
}

export function applyCuratedRule(draft, cueId, tier, id) {
  const cue = cuesById.get(cueId);
  if (!cue || cue.experimental || cue.event_type === "name_called" || !isAwareTier(tier)) return sanitizeAwareDraft(draft);
  if (cue.event_type !== "custom") return setAwareRule(draft, cue.event_type, tier);
  const rule = createCueRule(cueId, tier, id);
  const d = sanitizeAwareDraft(draft);
  if (d.custom_rules.some((r) => r.cue_id === cueId)) return d;
  return {...d, custom_rules:sanitizeCustomSounds([...d.custom_rules, rule])};
}

export function sanitizeCustomSounds(raw) {
  const seen = new Set();
  return (Array.isArray(raw) ? raw : [])
    .filter((r) => {
      if (!r || typeof r.id !== "string" || !r.id || r.id.length > 120 ||
          typeof r.label !== "string" || !isAwareTier(r.tier)) return false;
      const label = r.label.trim().replace(/\s+/g, " ");
      const key = label.toLocaleLowerCase();
      if (!label || label.length > 80 || seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 100)
    .map((r) => {
      const base = { id:r.id, label:r.label.trim().replace(/\s+/g, " "), tier:r.tier };
      if (r.status === "recognized" && r.cue_id) {
        return createCueRule(r.cue_id, r.tier, r.id) ?? {...base, status:"pending"};
      }
      const recognized = r.status === "recognized" && Array.isArray(r.model_labels) &&
        r.model_labels.length >= 1 && r.model_labels.length <= 4 &&
        r.model_labels.every((label) => catalogLabels.has(label) && label !== "Bicycle bell");
      return recognized
        ? {...base, status:"recognized", model_labels:[...new Set(r.model_labels)],
           icon:catalogLabels.get(r.model_labels[0]).icon,
           threshold:typeof r.threshold === "number" && r.threshold > 0 && r.threshold <= 1 ? r.threshold : .25}
        : {...base, status:"pending"};
    });
}

export function sanitizeAwareDraft(raw) {
  const d = raw && typeof raw === "object" ? raw : {};
  const rules = [];
  (Array.isArray(d.rules) ? d.rules : []).forEach((r) => {
    if (!r || !awareEvent(r.key) || !isAwareTier(r.tier)) return;
    const i = rules.findIndex((x) => x.key === r.key);
    if (i >= 0) rules[i] = { key: r.key, tier: r.tier };
    else rules.push({ key: r.key, tier: r.tier });
  });
  return {
    name: typeof d.name === "string" ? d.name : "",
    name_enabled: d.name_enabled !== false,
    aliasesText: typeof d.aliasesText === "string" ? d.aliasesText : "",
    mode: AWARE_PRESETS.some((m) => m.key === d.mode) ? d.mode : "balanced",
    rules,
    custom_rules: sanitizeCustomSounds(d.custom_rules),
    category_rules: Object.fromEntries(
      Object.entries(
        d.category_rules && typeof d.category_rules === "object"
          ? d.category_rules
          : {},
      ).filter(
        ([key, tier]) => key in alertPolicy.categories && isAwareTier(tier),
      ),
    ),
  };
}

// An explicit rule (any tier 0..4, including 0) wins; otherwise the preset default applies.
export function resolveAwareTier(draft, key) {
  const d = sanitizeAwareDraft(draft);
  const rule = d.rules.find((r) => r.key === key);
  if (rule) return { tier: rule.tier, source: "rule" };
  const category = alertPolicy.event_categories[key];
  if (category in d.category_rules)
    return { tier: d.category_rules[category], source: "category" };
  return { tier: AWARE_PRESET_DEFAULTS[d.mode][key], source: "preset" };
}

export function setAwareRule(draft, key, tier) {
  const d = sanitizeAwareDraft(draft);
  if (!awareEvent(key) || !isAwareTier(tier)) return d;
  const i = d.rules.findIndex((r) => r.key === key);
  const rules = d.rules.slice();
  if (i >= 0) rules[i] = { key, tier };
  else rules.push({ key, tier });
  return Object.assign({}, d, { rules });
}

export function removeAwareRule(draft, key) {
  const d = sanitizeAwareDraft(draft);
  return Object.assign({}, d, { rules: d.rules.filter((r) => r.key !== key) });
}

export function searchAwareSounds(query) {
  const q = String(query || "")
    .trim()
    .toLowerCase()
    .replace(/[_\s]+/g, " ");
  if (!q) return [];
  return AWARE_EVENTS.filter((e) => {
    const terms = [e.label.toLowerCase(), e.key.replace(/_/g, " ")].concat(
      e.terms,
    );
    return terms.some((t) => t.includes(q) || (q.length >= 4 && q.includes(t)));
  });
}

export function buildAwareProfile(draft) {
  const d = sanitizeAwareDraft(draft);
  const primary = d.name.trim().replace(/\s+/g, " ");
  const eventTiers = {};
  d.rules.forEach((r) => {
    eventTiers[r.key] = r.tier;
  });
  return {
    schema_version: 1,
    profile_id: "demo",
    revision: 1,
    display_name: primary,
    custom_sound_requests: d.custom_rules,
    name_detection: {
      enabled: primary.length > 0 && d.name_enabled !== false,
      primary_name: primary,
      aliases: parseAwareAliases(d.aliasesText, primary),
      language: "en",
    },
    notification_preferences: {
      mode: d.mode,
      category_tiers: d.category_rules,
      event_tiers: eventTiers,
    },
  };
}

// Display preferences: browser-only, stored apart from the profile until a display schema is agreed.
export const AWARE_DISPLAY_DEFAULTS = {
  labels: false,
  motion: "off",
  colors: { 1: "#b4b2aa", 2: "#f4f2ea", 3: "#f4f2ea", 4: "#ffb547" },
};

export function sanitizeAwareDisplay(raw) {
  const d = raw && typeof raw === "object" ? raw : {};
  const colors = {};
  [1, 2, 3, 4].forEach((t) => {
    const c = d.colors && d.colors[t];
    colors[t] =
      typeof c === "string" && /^#[0-9a-f]{6}$/i.test(c)
        ? c
        : AWARE_DISPLAY_DEFAULTS.colors[t];
  });
  return {
    labels: d.labels === true,
    motion: d.motion === "pulse" ? "pulse" : "off",
    colors,
  };
}
// --- end profile logic ---

const AWARE_DRAFT_KEY = "aware.profile-draft.v2";
const AWARE_LEGACY_KEY = "aware.profile-draft.v1";
const AWARE_DISPLAY_KEY = "aware.display-prefs.v2"; // v2: night-lens palette

function awareKey(base) {
  return base + ":local-demo";
}

function awareStorageAvailable() {
  try {
    window.localStorage.setItem("__aware_probe__", "1");
    window.localStorage.removeItem("__aware_probe__");
    return true;
  } catch (e) {
    return false;
  }
}

function readAwareStored(base) {
  try {
    const s = window.localStorage.getItem(awareKey(base));
    return s ? JSON.parse(s) : null;
  } catch (e) {
    return null;
  }
}

function readAwareDraft() {
  const v2 = readAwareStored(AWARE_DRAFT_KEY);
  if (v2) return sanitizeAwareDraft(v2);
  const v1 = readAwareStored(AWARE_LEGACY_KEY);
  // Earlier drafts used word tiers; keep their name and preset, drop the old tier values.
  if (v1)
    return sanitizeAwareDraft({
      name: v1.name,
      aliasesText: v1.aliasesText,
      mode: v1.mode,
      rules: [],
    });
  return null;
}

function awareReadableOn(hex) {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255,
    g = (n >> 8) & 255,
    b = n & 255;
  return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#0b0b0b" : "#ffffff";
}

// Local integration: use the same cue and one-bit renderer as the companion.
export function AwareCuePreview({
  ev,
  tier,
  display,
  render,
  direction,
  motionOn,
  playKey,
}) {
  const bearing = direction === "unknown" ? null : Number(direction);
  const coarse = directionBucket(bearing, bearing === null ? null : 1);
  const event = {
    ...makeMock(ev.key, tier),
    direction_degrees: bearing, direction_confidence: bearing === null ? null : 1,
    event_id: "onboarding-" + playKey,
    label: ev.cue,
  };
  const appearance = {
    text: display.labels ? "labels" : "icons",
    motion: motionOn ? "gentle" : "none",
    colors: { 0: "#ffffff", ...display.colors },
    direction,
  };
  return (
    <div
      className={`onboarding-cue-preview ${render === "oled" ? "onboarding-oled" : ""}`}
    >
      {render === "oled" ? (
        <Oled
          event={event}
          labels={appearance.text === "labels"}
          direction={coarse}
        />
      ) : (
        <div
          className={`lens-frame ${motionOn ? "gentle-cue" : ""}`}
          style={{
            filter: `drop-shadow(0 0 5px ${display.colors[tier] ?? "#ffffff"})`,
          }}
        >
          <Oled
            event={event}
            labels={appearance.text === "labels"}
            direction={coarse}
            lens
          />
        </div>
      )}
    </div>
  );
}

export default function AwareOnboarding({ onChange, onComplete, theme, receiverProfile } = {}) {
  const isDark = theme === "dark";
  const uid = useId();
  const [storageOk] = useState(() => awareStorageAvailable());
  const [restored] = useState(() =>
    awareStorageAvailable() ? readAwareDraft() : null,
  );
  const [draft, setDraftState] = useState(() => restored || AWARE_EMPTY_DRAFT);
  const [display, setDisplayState] = useState(() =>
    sanitizeAwareDisplay(
      awareStorageAvailable() ? readAwareStored(AWARE_DISPLAY_KEY) : null,
    ),
  );
  const [editRevision, setEditRevision] = useState(0);
  const setDraft = React.useCallback((value) => { setEditRevision((n) => n+1); setDraftState(value); }, []);
  const setDisplay = React.useCallback((value) => { setEditRevision((n) => n+1); setDisplayState(value); }, []);
  useEffect(() => {
    if (!receiverProfile) return;
    const names = receiverProfile.name_detection;
    const prefs = receiverProfile.notification_preferences;
    setDraftState(sanitizeAwareDraft({
      name: names.primary_name, name_enabled: names.enabled,
      aliasesText: names.aliases.join(", "), mode: prefs.mode,
      rules: Object.entries(prefs.event_tiers ?? {}).map(([key,tier]) => ({key,tier})),
      custom_rules: receiverProfile.custom_sound_requests ?? [], category_rules: prefs.category_tiers ?? {},
    }));
    if (receiverProfile.display) setDisplayState((old) => ({...old, labels: receiverProfile.display.labels === true}));
  }, [receiverProfile]);
  const [saveState, setSaveState] = useState(() => ({
    kind: restored ? "restored" : "new",
  }));
  const [query, setQuery] = useState("");
  const [pending, setPending] = useState(null); // { key, tier }
  const [customNote, setCustomNote] = useState("");
  const [confirmReset, setConfirmReset] = useState(false);
  const [previewKey, setPreviewKey] = useState("smoke_alarm");
  const [direction, setDirection] = useState("unknown");
  const [render, setRender] = useState("browser");
  const [playKey, setPlayKey] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const firstRun = useRef(true);
  const searchRef = useRef(null);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReducedMotion(mq.matches);
    onChange();
    if (mq.addEventListener) {
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    }
    mq.addListener(onChange);
    return () => mq.removeListener(onChange);
  }, []);

  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    if (!storageOk) return;
    try {
      window.localStorage.setItem(
        awareKey(AWARE_DRAFT_KEY),
        JSON.stringify(draft),
      );
      window.localStorage.setItem(
        awareKey(AWARE_DISPLAY_KEY),
        JSON.stringify(display),
      );
      setSaveState({ kind: "saved", at: Date.now() });
    } catch (e) {
      setSaveState({ kind: "failed" });
    }
  }, [draft, display, storageOk]);

  const profile = useMemo(() => buildAwareProfile(draft), [draft]);
  useEffect(() => {
    onChange?.({ profile, display, direction: directionBucket(direction === "unknown" ? null : Number(direction), direction === "unknown" ? null : 1) ?? "unknown", editRevision });
  }, [profile, display, direction, editRevision, onChange]);
  const ruleCount = draft.rules.length;
  const primary = profile.name_detection.primary_name;
  const preset = AWARE_PRESETS.find((m) => m.key === draft.mode);
  const presetTiers = AWARE_PRESET_DEFAULTS[draft.mode];
  const ruleKeys = new Set(draft.rules.map((r) => r.key));
  const matches = useMemo(() => searchAwareSounds(query), [query]);
  const curatedMatches = useMemo(() => searchCuratedSounds(query), [query]);
  const selectedCueIds = new Set([
    ...(draft.custom_rules ?? []).map((rule) => rule.cue_id),
    ...cueCatalog.cues.filter((cue) => cue.event_type !== "custom" && ruleKeys.has(cue.event_type)).map((cue) => cue.id),
  ]);
  const catalogMatches = useMemo(() => {
    const q = normalizeSearch(query);
    if (q.length < 2) return [];
    const selected = new Set((draft.custom_rules ?? []).flatMap((r) => r.model_labels ?? []));
    const words = q.split(" ");
    return modelCatalog.sounds.filter((sound) => !selected.has(sound.label) && !curatedModelLabels.has(sound.label) && sound.label !== "Bicycle bell" &&
      words.every((word) => normalizeSearch(`${sound.name} ${sound.label} ${sound.category}`).includes(word))).slice(0,8);
  }, [query, draft.custom_rules]);
  const available = matches.filter((e) => !ruleKeys.has(e.key));
  const alreadyAdded = matches.filter((e) => ruleKeys.has(e.key));

  const p = isDark
    ? {
        ink: "#f4f2ea",
        muted: "#9a988f",
        line: "rgba(236,236,234,0.12)",
        lineStrong: "rgba(236,236,234,0.32)",
        field: "rgba(236,236,234,0.04)",
        tint: "rgba(236,236,234,0.06)",
        btnBg: "#ececea",
        btnFg: "#1c1d19",
      }
    : {
        ink: "#1c1d19",
        muted: "#5c5e57",
        line: "rgba(28,29,25,0.12)",
        lineStrong: "rgba(28,29,25,0.3)",
        field: "#ffffff",
        tint: "rgba(28,29,25,0.035)",
        btnBg: "#1c1d19",
        btnFg: "#fafaf8",
      };
  const font = '"Instrument Sans", Inter, ui-sans-serif, system-ui, sans-serif';
  const mono = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

  const s = {
    section: {
      marginTop: 36,
      paddingTop: 32,
      borderTop: "1px solid " + p.line,
    },
    h2: { fontSize: 17, fontWeight: 600, margin: 0, letterSpacing: "-0.005em" },
    lead: { fontSize: 15, color: p.muted, margin: "6px 0 0" },
    label: { display: "block", fontSize: 15, fontWeight: 500, marginBottom: 8 },
    help: { fontSize: 14, color: p.muted, margin: "8px 0 0" },
    input: {
      width: "100%",
      boxSizing: "border-box",
      height: 44,
      padding: "0 12px",
      fontSize: 15,
      fontFamily: font,
      color: p.ink,
      background: p.field,
      border: "1px solid " + p.lineStrong,
      borderRadius: 10,
    },
    select: {
      height: 40,
      padding: "0 8px",
      fontSize: 15,
      fontFamily: font,
      color: p.ink,
      background: p.field,
      border: "1px solid " + p.lineStrong,
      borderRadius: 10,
      maxWidth: "100%",
      colorScheme: isDark ? "dark" : "light",
    },
    group: {
      border: "1px solid " + p.line,
      borderRadius: 12,
      overflow: "hidden",
    },
    row: (i) => ({ borderTop: i ? "1px solid " + p.line : "none" }),
    primaryBtn: {
      height: 44,
      padding: "0 20px",
      fontSize: 15,
      fontWeight: 500,
      fontFamily: font,
      color: p.btnFg,
      background: p.btnBg,
      border: "none",
      borderRadius: 9999,
      cursor: "pointer",
    },
    quietBtn: {
      height: 40,
      padding: "0 14px",
      fontSize: 15,
      fontFamily: font,
      color: p.ink,
      background: "transparent",
      border: "1px solid " + p.lineStrong,
      borderRadius: 9999,
      cursor: "pointer",
    },
    textBtn: {
      height: 40,
      padding: "0 4px",
      fontSize: 15,
      fontFamily: font,
      color: p.muted,
      background: "transparent",
      border: "none",
      cursor: "pointer",
      textDecoration: "underline",
      textUnderlineOffset: 3,
    },
    summary: { fontSize: 17, fontWeight: 600, padding: "4px 0" },
    radio: {
      marginTop: 4,
      width: 18,
      height: 18,
      accentColor: p.ink,
      flexShrink: 0,
    },
    radioRow: (on, i) => ({
      display: "flex",
      gap: 14,
      alignItems: "flex-start",
      padding: "12px 16px",
      cursor: "pointer",
      background: on ? p.tint : "transparent",
      borderTop: i ? "1px solid " + p.line : "none",
    }),
    inlineRadio: {
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      minHeight: 40,
      marginRight: 20,
      cursor: "pointer",
    },
  };

  const update = (patch) => setDraft((d) => Object.assign({}, d, patch));
  const updateDisplay = (patch) =>
    setDisplay((d) => sanitizeAwareDisplay(Object.assign({}, d, patch)));
  const tierText = (v) => awareTierLabel(v) + " (" + v + ")";

  const startRule = (key) => {
    setPending({ key, tier: null });
    setQuery("");
  };
  const confirmRule = () => {
    if (!pending || !isAwareTier(pending.tier)) return;
    if (pending.cue_id) {
      const cue = cuesById.get(pending.cue_id);
      if (!cue || cue.experimental || cue.event_type === "name_called") return;
      setDraft((d) => applyCuratedRule(d, pending.cue_id, pending.tier, crypto.randomUUID()));
      if (cue.event_type !== "custom") setPreviewKey(cue.event_type);
      setCustomNote(`${cue.label} priority saved. Recognition sensitivity still needs real-room testing.`);
    } else {
      setDraft((d) => setAwareRule(d, pending.key, pending.tier));
      setPreviewKey(pending.key);
    }
    setPending(null);
  };
  const changeRule = (key, tier) => {
    setDraft((d) => setAwareRule(d, key, tier));
    setPreviewKey(key);
  };
  const resetRule = (key) => setDraft((d) => removeAwareRule(d, key));

  const resetAll = () => {
    setDraft(AWARE_EMPTY_DRAFT);
    setDisplay(sanitizeAwareDisplay(null));
    setPending(null);
    setQuery("");
    setConfirmReset(false);
  };

  const statusText =
    !storageOk || saveState.kind === "failed"
      ? "Settings apply for this visit, but could not be saved in this browser."
      : "Settings save automatically on this browser.";

  const previewEv = awareEvent(previewKey) || AWARE_EVENTS[0];
  const previewResolved = resolveAwareTier(draft, previewEv.key);
  const motionOn =
    display.motion === "pulse" && !reducedMotion && render === "browser";
  const pendingEv = pending ? (pending.cue_id ? cuesById.get(pending.cue_id) : awareEvent(pending.key)) : null;

  return (
    <div
      className="aware-root"
      style={{
        width: "100%",
        color: p.ink,
        fontFamily: font,
        fontSize: 15,
        lineHeight: 1.55,
      }}
    >
      <style>
        {".aware-root :focus-visible{outline:2px solid " +
          p.ink +
          ";outline-offset:2px}.aware-root summary{cursor:pointer}" +
          "@keyframes aware-pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}" +
          "@media (prefers-reduced-motion: reduce){.aware-pulse{animation:none!important}}"}
      </style>
      <div
        style={{
          maxWidth: 640,
          margin: "0 auto",
          padding: "40px 20px 72px",
          boxSizing: "border-box",
        }}
      >
        <h1
          style={{
            fontSize: 26,
            fontWeight: 600,
            letterSpacing: "-0.01em",
            margin: 0,
          }}
        >
          Your preferences
        </h1>
        <p style={{ fontSize: 16, margin: "8px 0 0" }}>
          Stay aware of the sounds that matter to you, without watching a
          screen. Start from a preset, then add exceptions. Changes apply to the
          preview right away and to the receiver whenever it is connected.
        </p>
        <div
          role="status"
          aria-live="polite"
          style={{ marginTop: 14, fontSize: 14, color: p.muted }}
        >
          <div>{statusText}</div>
        </div>

        {/* Preset */}
        <section style={s.section}>
          <fieldset
            style={{ border: "none", margin: 0, padding: 0, minWidth: 0 }}
          >
            <legend style={Object.assign({}, s.h2, { padding: 0 })}>
              Preset
            </legend>
            <p style={s.lead}>
              Sets the default priority for every supported sound. Changing it
              keeps your rules.
            </p>
            <div style={Object.assign({}, s.group, { marginTop: 20 })}>
              {AWARE_PRESETS.map((m, i) => {
                const on = draft.mode === m.key;
                return (
                  <label key={m.key} style={s.radioRow(on, i)}>
                    <input
                      type="radio"
                      name={uid + "-mode"}
                      value={m.key}
                      checked={on}
                      onChange={() => update({ mode: m.key })}
                      style={s.radio}
                    />
                    <span>
                      <span
                        style={{ display: "block", fontWeight: on ? 600 : 500 }}
                      >
                        {m.label}
                      </span>
                      <span
                        style={{
                          display: "block",
                          fontSize: 14,
                          color: p.muted,
                        }}
                      >
                        {m.hint}
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
          <div style={{ marginTop: 20 }}>
            <div style={{ fontWeight: 500 }}>{preset.label} defaults</div>
            <dl
              style={{
                margin: "8px 0 0",
                display: "grid",
                gridTemplateColumns: "max-content 1fr",
                columnGap: 16,
                rowGap: 4,
                fontSize: 15,
              }}
            >
              {[4, 3, 2, 1, 0].map((t) => {
                const names = AWARE_EVENTS.filter(
                  (e) => presetTiers[e.key] === t,
                ).map((e) => e.label);
                if (!names.length) return null;
                return (
                  <React.Fragment key={t}>
                    <dt style={{ color: p.muted }}>{tierText(t)}</dt>
                    <dd style={{ margin: 0 }}>{names.join(", ")}</dd>
                  </React.Fragment>
                );
              })}
            </dl>
            {draft.mode !== "balanced" && (
              <p style={s.help}>
                {preset.label} defaults are provisional; only Balanced is agreed
                so far. You can change any sound below.
              </p>
            )}
          </div>
        </section>

        <section style={s.section}>
          <details>
            <summary style={s.summary}>Category defaults (optional)</summary>
            <p style={s.help}>
              Change a group together. Individual sound rules take priority;
              otherwise the selected preset applies.
            </p>
            {Object.entries(alertPolicy.categories).map(([key, label]) => (
              <label
                key={key}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  alignItems: "center",
                  marginTop: 12,
                }}
              >
                {label}
                <select
                  aria-label={`Priority for category ${label}`}
                  style={s.select}
                  value={draft.category_rules?.[key] ?? ""}
                  onChange={(e) =>
                    setDraft((d) => {
                      const categories = { ...d.category_rules };
                      if (e.target.value === "") delete categories[key];
                      else categories[key] = Number(e.target.value);
                      return { ...d, category_rules: categories };
                    })
                  }
                >
                  <option value="">Use preset</option>
                  {AWARE_TIERS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </details>
        </section>

        {/* Rules */}
        <section style={s.section} aria-labelledby={uid + "-rules-h"}>
          <h2 id={uid + "-rules-h"} style={s.h2}>
            Sound rules
          </h2>
          <p style={s.lead}>
            Search for a sound to change how it gets your attention.
          </p>

          {!pending && (
            <div style={{ marginTop: 20 }}>
              <label htmlFor={uid + "-search"} style={s.label}>
                Find a sound
              </label>
              <input
                id={uid + "-search"}
                ref={searchRef}
                type="search"
                value={query}
                autoComplete="off"
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (curatedMatches.length || available.length)) {
                    e.preventDefault();
                    const cue = curatedMatches.find((c) => !c.experimental && c.event_type !== "name_called" && !selectedCueIds.has(c.id));
                    if (cue) setPending({cue_id:cue.id, tier:cue.default_tier});
                    else if (available.length && !curatedMatches.length) startRule(available[0].key);
                  }
                }}
                aria-describedby={uid + "-search-help"}
                aria-controls={uid + "-results"}
                style={s.input}
              />
              <p id={uid + "-search-help"} style={s.help}>
                Defaults are already set. Search for a sound you want to change; add only the exceptions that matter to you.
              </p>
              <div id={uid + "-results"} aria-live="polite">
                {curatedMatches.length > 0 && <ul style={{...s.group, listStyle:"none", padding:0, marginTop:12}}>
                  {curatedMatches.slice(0,8).map((cue, i) => <li key={cue.id} style={s.row(i)}>
                    <button type="button" style={{...s.textBtn, width:"100%", textAlign:"left", textDecoration:"none", padding:"14px 16px"}}
                      disabled={cue.experimental || selectedCueIds.has(cue.id) || ((draft.custom_rules ?? []).length >= 100 && cue.event_type === "custom")}
                      onClick={() => {
                        if (cue.event_type === "name_called") {
                          const input = document.getElementById(uid + "-name");
                          const section = input?.closest("details");
                          if (section) section.open = true;
                          input?.focus();
                          return;
                        }
                        setPending({cue_id:cue.id, tier:cue.default_tier}); setQuery("");
                      }}>
                      <span style={{display:"block", fontWeight:500}}>{cue.label}</span>
                      <span style={{display:"block", color:p.muted, fontSize:14, marginTop:4}}>
                        {cue.experimental ? "Experimental · awaiting recognition tests" : selectedCueIds.has(cue.id) ? "Already added · change its priority below" : cue.event_type === "name_called" ? "Set your name · uses speech recognition" : `${cue.category} · suggested ${awareTierLabel(cue.default_tier)}`}
                      </span>
                    </button>
                  </li>)}
                </ul>}
                {catalogMatches.length > 0 && <details style={{marginTop:12}}>
                  <summary style={{...s.textBtn, cursor:"pointer"}}>More model labels</summary>
                  <p style={s.help}>Advanced matches from the raw classifier. These use broader category icons.</p>
                {catalogMatches.length > 0 && <ul style={{...s.group, listStyle:"none", padding:0, marginTop:12}}>
                  {catalogMatches.map((sound) => <li key={sound.label} style={{padding:12}}>
                    <button type="button" style={s.textBtn} disabled={(draft.custom_rules ?? []).length >= 100}
                      onClick={() => {
                        const next = sanitizeCustomSounds([...(draft.custom_rules ?? []), {
                          id:crypto.randomUUID(), label:sound.name, tier:2, status:"recognized",
                          model_labels:[sound.label], icon:sound.icon,
                        }]);
                        setDraft((d) => ({...d, custom_rules:next}));
                        setCustomNote(`${sound.name} added from the model catalog. Choose its priority below; recognition sensitivity is provisional.`);
                        setQuery("");
                      }}>
                      Add {sound.name} · {sound.category}
                    </button>
                  </li>)}
                </ul>}
                </details>}
                {query.trim() && curatedMatches.length === 0 && (
                  <button
                    type="button"
                    style={{ ...s.textBtn, marginTop: 12 }}
                    disabled={
                      query.trim().length > 80 ||
                      (draft.custom_rules ?? []).length >= 100
                    }
                    onClick={() => {
                      const before = draft.custom_rules ?? [];
                      const next = sanitizeCustomSounds([
                        ...before,
                        { id: crypto.randomUUID(), label: query, tier: 2 },
                      ]);
                      if (next.length === before.length) {
                        setCustomNote("That custom sound is already listed.");
                        return;
                      }
                      setDraft((d) => ({ ...d, custom_rules: next }));
                      setQuery("");
                      setCustomNote(
                        "Custom sound saved. Recognition is pending; it is not being detected yet.",
                      );
                    }}
                  >
                    Request “{query.trim()}” as a custom sound
                  </button>
                )}
                {customNote && (
                  <p role="status" style={s.help}>
                    {customNote}
                  </p>
                )}

                {query.trim() !== "" && available.length > 0 && curatedMatches.length === 0 && (
                  <ul
                    style={Object.assign({}, s.group, {
                      listStyle: "none",
                      margin: "12px 0 0",
                      padding: 0,
                    })}
                  >
                    {available.map((e, i) => (
                      <li key={e.key} style={s.row(i)}>
                        <button
                          type="button"
                          onClick={() => startRule(e.key)}
                          style={{
                            width: "100%",
                            textAlign: "left",
                            display: "flex",
                            flexWrap: "wrap",
                            justifyContent: "space-between",
                            gap: "4px 16px",
                            padding: "12px 16px",
                            background: "transparent",
                            border: "none",
                            color: p.ink,
                            fontFamily: font,
                            fontSize: 15,
                            cursor: "pointer",
                          }}
                        >
                          <span>
                            <span style={{ display: "block", fontWeight: 500 }}>
                              {e.label}
                            </span>
                            {e.hint && (
                              <span
                                style={{
                                  display: "block",
                                  fontSize: 14,
                                  color: p.muted,
                                }}
                              >
                                {e.hint}
                              </span>
                            )}
                          </span>
                          <span style={{ fontSize: 14, color: p.muted }}>
                            {preset.label}: {tierText(presetTiers[e.key])}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {query.trim() !== "" &&
                  available.length === 0 &&
                  alreadyAdded.length > 0 && (
                    <p style={s.help}>
                      {alreadyAdded.map((e) => e.label).join(", ")} already{" "}
                      {alreadyAdded.length === 1 ? "has a rule" : "have rules"}{" "}
                      below.
                    </p>
                  )}
                {query.trim() !== "" && matches.length === 0 && catalogMatches.length === 0 && curatedMatches.length === 0 && (
                  <div
                    style={{
                      marginTop: 12,
                      padding: "14px 16px",
                      border: "1px solid " + p.line,
                      borderRadius: 12,
                    }}
                  >
                    <div style={{ fontWeight: 500 }}>
                      No supported sound matches “{query.trim()}”.
                    </div>
                    <p style={Object.assign({}, s.help, { marginTop: 4 })}>
                      Aware can only react to sounds its classifier has been
                      trained to recognize. Typing a new name here would not
                      teach it that sound. You can request it below and choose
                      its priority; recognition will stay pending until support
                      is connected.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {pending && pendingEv && (
            <div
              style={{
                marginTop: 20,
                padding: "16px",
                border: "1px solid " + p.lineStrong,
                borderRadius: 12,
              }}
            >
              <fieldset
                style={{ border: "none", margin: 0, padding: 0, minWidth: 0 }}
              >
                <legend style={{ padding: 0, fontWeight: 600, fontSize: 16 }}>
                  Priority for {pendingEv.label}
                </legend>
                <p style={Object.assign({}, s.help, { marginTop: 2 })}>
                  {pending.cue_id ? `Suggested: ${tierText(pendingEv.default_tier)}.` : `${preset.label} preset: ${tierText(presetTiers[pendingEv.key])}.`}
                  {pendingEv.hint ? " " + pendingEv.hint : ""}
                </p>
                <div style={Object.assign({}, s.group, { marginTop: 12 })}>
                  {AWARE_TIERS.map((t, i) => {
                    const on = pending.tier === t.value;
                    return (
                      <label key={t.value} style={s.radioRow(on, i)}>
                        <input
                          type="radio"
                          name={uid + "-pending"}
                          checked={on}
                          onChange={() =>
                            setPending({ ...pending, tier: t.value })
                          }
                          style={s.radio}
                        />
                        <span>
                          <span
                            style={{
                              display: "block",
                              fontWeight: on ? 600 : 500,
                            }}
                          >
                            {t.label} ({t.value})
                          </span>
                          <span
                            style={{
                              display: "block",
                              fontSize: 14,
                              color: p.muted,
                            }}
                          >
                            {t.hint}
                          </span>
                        </span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 12,
                  alignItems: "center",
                  marginTop: 16,
                }}
              >
                <button
                  type="button"
                  onClick={confirmRule}
                  disabled={!isAwareTier(pending.tier)}
                  style={Object.assign(
                    {},
                    s.primaryBtn,
                    isAwareTier(pending.tier)
                      ? {}
                      : { opacity: 0.4, cursor: "not-allowed" },
                  )}
                >
                  Add rule
                </button>
                <button
                  type="button"
                  onClick={() => setPending(null)}
                  style={s.textBtn}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div style={{ marginTop: 24 }}>
            <div style={{ fontWeight: 500 }}>Your rules</div>
            {ruleCount === 0 ? (
              <p style={Object.assign({}, s.help, { marginTop: 4 })}>
                {draft.custom_rules.length ? `Built-in sounds follow the ${preset.label} preset. Your added sounds are below.` : `No rules yet. Every sound follows the ${preset.label} preset.`}
              </p>
            ) : (
              <ul
                style={Object.assign({}, s.group, {
                  listStyle: "none",
                  margin: "10px 0 0",
                  padding: 0,
                })}
              >
                {draft.rules.map((r, i) => {
                  const ev = awareEvent(r.key);
                  return (
                    <li
                      key={r.key}
                      style={Object.assign(
                        {
                          display: "flex",
                          flexWrap: "wrap",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "8px 16px",
                          padding: "10px 16px",
                        },
                        s.row(i),
                      )}
                    >
                      <span style={{ flex: "1 1 160px" }}>
                        <span style={{ display: "block", fontWeight: 500 }}>
                          {ev.label}
                        </span>
                        <span
                          style={{
                            display: "block",
                            fontSize: 14,
                            color: p.muted,
                          }}
                        >
                          Preset would be {tierText(presetTiers[r.key])}
                        </span>
                      </span>
                      <span
                        style={{
                          display: "inline-flex",
                          flexWrap: "wrap",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        <select
                          aria-label={"Priority for " + ev.label}
                          value={String(r.tier)}
                          onChange={(e) =>
                            changeRule(r.key, Number(e.target.value))
                          }
                          style={s.select}
                        >
                          {AWARE_TIERS.map((t) => (
                            <option key={t.value} value={String(t.value)}>
                              {t.label} ({t.value})
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => resetRule(r.key)}
                          style={s.textBtn}
                          aria-label={"Reset " + ev.label + " to preset"}
                        >
                          Reset to preset
                        </button>
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </section>

        {(draft.custom_rules ?? []).length > 0 && (
          <section style={s.section} aria-label="Added sounds">
            <h2 style={s.h2}>Added sounds</h2>
            <p style={s.lead}>
              Catalog sounds can trigger alerts while the recognizer is running. Free-text requests stay pending until recognition is connected.
            </p>
            <ul style={{ listStyle: "none", padding: 0, marginTop: 16 }}>
              {draft.custom_rules.map((rule) => (
                <li
                  key={rule.id}
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 12,
                    alignItems: "center",
                    padding: "12px 0",
                  }}
                >
                  <span style={{ flex: 1, minWidth: 140 }}>
                    {rule.label}
                    <small style={{ display: "block", color: p.muted }}>
                      {rule.status === "recognized" ? (rule.cue_id ? "Sound cue · sensitivity provisional" : "Model label · sensitivity provisional") : "Recognition pending"}
                    </small>
                  </span>
                  <select
                    aria-label={`Priority for custom sound ${rule.label}`}
                    value={rule.tier}
                    style={s.select}
                    onChange={(e) =>
                      setDraft((d) => ({
                        ...d,
                        custom_rules: d.custom_rules.map((r) =>
                          r.id === rule.id
                            ? { ...r, tier: Number(e.target.value) }
                            : r,
                        ),
                      }))
                    }
                  >
                    {AWARE_TIERS.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    style={s.textBtn}
                    aria-label={`Remove custom sound ${rule.label}`}
                    onClick={() =>
                      setDraft((d) => ({
                        ...d,
                        custom_rules: d.custom_rules.filter(
                          (r) => r.id !== rule.id,
                        ),
                      }))
                    }
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Name */}
        <section style={s.section}>
          <details>
            <summary style={s.summary}>
              Name (optional){" "}
              <span
                style={{
                  fontWeight: 400,
                  fontSize: 15,
                  color: p.muted,
                  marginLeft: 6,
                }}
              >
                {primary ? "Name configured" : "Off"}
              </span>
            </summary>
            <div style={{ marginTop: 16 }}>
              <label htmlFor={uid + "-name"} style={s.label}>
                Name
              </label>
              <input
                id={uid + "-name"}
                type="text"
                autoComplete="given-name"
                value={draft.name}
                onChange={(e) => update({ name: e.target.value, name_enabled: true })}
                aria-describedby={uid + "-name-help"}
                style={s.input}
              />
              <p id={uid + "-name-help"} style={s.help}>
                {primary
                  ? (draft.name_enabled ? "Your name is saved for the speech recognizer. Live recognition needs the speech worker running." : "Your name is saved. Name detection is currently disabled on the receiver.")
                  : "Leave blank to keep name detection off."}
              </p>
            </div>
            <div style={{ marginTop: 20 }}>
              <label htmlFor={uid + "-aliases"} style={s.label}>
                Other names
              </label>
              <input
                id={uid + "-aliases"}
                type="text"
                value={draft.aliasesText}
                onChange={(e) => update({ aliasesText: e.target.value })}
                aria-describedby={uid + "-aliases-help"}
                style={s.input}
              />
              <p id={uid + "-aliases-help"} style={s.help}>
                {!primary && profile.name_detection.aliases.length
                  ? "These are kept, but name detection stays off until you add a name."
                  : "Nicknames or spellings people use, separated by commas (for example: Sam, Sammy)."}
              </p>
            </div>
          </details>
        </section>

        {/* Display preferences */}
        <section style={s.section}>
          <details>
            <summary style={s.summary}>
              Display preferences{" "}
              <span
                style={{
                  fontWeight: 400,
                  fontSize: 15,
                  color: p.muted,
                  marginLeft: 6,
                }}
              >
                Labels reach the glasses
              </span>
            </summary>
            <p style={Object.assign({}, s.lead, { marginTop: 12 })}>
              See how your cues will look. Labels also apply to the glasses;
              colors, motion and placement are browser-only.
            </p>

            <div style={{ marginTop: 20 }}>
              <div style={{ fontWeight: 500 }}>Cue style</div>
              <p style={Object.assign({}, s.help, { marginTop: 2 })}>
                Non-urgent cues show an icon first. Urgent cues always add short
                text.
              </p>
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  minHeight: 40,
                  marginTop: 6,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={display.labels}
                  onChange={(e) => updateDisplay({ labels: e.target.checked })}
                  style={{ width: 18, height: 18, accentColor: p.ink }}
                />
                Show short labels with icons
              </label>
            </div>

            <div style={{ marginTop: 20 }}>
              <div style={{ fontWeight: 500 }}>Browser glow by priority</div>
              <p style={Object.assign({}, s.help, { marginTop: 2 })}>
                The browser glow uses these colors. The OLED pixels stay white;
                frames and the urgent label communicate priority.
              </p>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                  gap: 12,
                  marginTop: 10,
                }}
              >
                {[1, 2, 3, 4].map((t) => (
                  <label
                    key={t}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      minHeight: 40,
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="color"
                      value={display.colors[t]}
                      onChange={(e) =>
                        updateDisplay({
                          colors: Object.assign({}, display.colors, {
                            [t]: e.target.value,
                          }),
                        })
                      }
                      style={{
                        width: 40,
                        height: 32,
                        padding: 0,
                        border: "1px solid " + p.lineStrong,
                        borderRadius: 8,
                        background: "transparent",
                        cursor: "pointer",
                      }}
                    />
                    {tierText(t)}
                  </label>
                ))}
              </div>
              <button
                type="button"
                onClick={() =>
                  updateDisplay({ colors: AWARE_DISPLAY_DEFAULTS.colors })
                }
                style={Object.assign({}, s.textBtn, { marginTop: 4 })}
              >
                Reset colors
              </button>
            </div>

            <fieldset
              style={{
                border: "none",
                margin: "20px 0 0",
                padding: 0,
                minWidth: 0,
              }}
            >
              <legend style={{ padding: 0, fontWeight: 500 }}>Motion</legend>
              <div style={{ marginTop: 4 }}>
                <label style={s.inlineRadio}>
                  <input
                    type="radio"
                    name={uid + "-motion"}
                    checked={display.motion === "off"}
                    onChange={() => updateDisplay({ motion: "off" })}
                    style={{ width: 18, height: 18, accentColor: p.ink }}
                  />
                  Off
                </label>
                <label style={s.inlineRadio}>
                  <input
                    type="radio"
                    name={uid + "-motion"}
                    checked={display.motion === "pulse"}
                    onChange={() => {
                      updateDisplay({ motion: "pulse" });
                      setPlayKey((k) => k + 1);
                    }}
                    style={{ width: 18, height: 18, accentColor: p.ink }}
                  />
                  Gentle pulse (two cycles)
                </label>
              </div>
              {display.motion === "pulse" && reducedMotion && (
                <p style={s.help}>
                  Your system asks for reduced motion, so the pulse stays off.
                </p>
              )}
            </fieldset>

            <div style={{ marginTop: 28 }}>
              <div style={{ fontWeight: 500 }}>Preview</div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 12,
                  alignItems: "flex-end",
                  marginTop: 10,
                }}
              >
                <label
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                    fontSize: 14,
                    color: p.muted,
                  }}
                >
                  Sound
                  <select
                    value={previewEv.key}
                    onChange={(e) => {
                      setPreviewKey(e.target.value);
                      setPlayKey((k) => k + 1);
                    }}
                    style={s.select}
                  >
                    {AWARE_EVENTS.map((e) => (
                      <option key={e.key} value={e.key}>
                        {e.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                    fontSize: 14,
                    color: p.muted,
                  }}
                >
                  Arrow bearing (simulated)
                  <select
                    aria-label="Preview arrow bearing"
                    value={direction}
                    onChange={(e) => {
                      setDirection(e.target.value);
                      setPlayKey((k) => k + 1);
                    }}
                    style={s.select}
                  >
                    <option value="unknown">No direction arrow</option>
                    {Array.from({length:16},(_,i) => {
                      const angle=i*22.5, signed=angle>180?angle-360:angle;
                      return <option key={i} value={String(signed)}>{signed}° · simulated</option>;
                    })}
                  </select>
                </label>
                <label
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                    fontSize: 14,
                    color: p.muted,
                  }}
                >
                  Display
                  <select
                    value={render}
                    onChange={(e) => setRender(e.target.value)}
                    style={s.select}
                  >
                    <option value="browser">Browser mirror</option>
                    <option value="oled">SSD1306 (monochrome)</option>
                  </select>
                </label>
                {motionOn && (
                  <button
                    type="button"
                    onClick={() => setPlayKey((k) => k + 1)}
                    style={s.quietBtn}
                  >
                    Play again
                  </button>
                )}
              </div>
              <div style={{ marginTop: 14 }} aria-hidden="true">
                <AwareCuePreview
                  ev={previewEv}
                  tier={previewResolved.tier}
                  display={display}
                  render={render}
                  direction={direction}
                  motionOn={motionOn}
                  playKey={playKey}
                  mono={mono}
                />
              </div>
              <p
                style={Object.assign({}, s.help, {
                  color: p.ink,
                  marginTop: 12,
                })}
              >
                {previewEv.label}: {tierText(previewResolved.tier)},{" "}
                {previewResolved.source === "rule"
                  ? "from your rule"
                  : "from the " + preset.label + " preset"}
                .
              </p>
              <p style={s.help}>
                The icon and priority box stay centered inside the fixed right-side display patch.
                Only the surrounding arrow changes with direction. These preview bearings are simulated;
                live arrows require a supported bearing. Unknown direction has no arrow.
              </p>
            </div>
          </details>
        </section>

        <section style={s.section} aria-label="Finish setup">
          <p style={s.lead}>You can change these preferences anytime.</p>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: 12,
              marginTop: 20,
            }}
          >
            <button type="button" onClick={onComplete} style={s.primaryBtn}>
              Start preview
            </button>
            {!confirmReset ? (
              <button
                type="button"
                onClick={() => setConfirmReset(true)}
                style={s.textBtn}
              >
                Start over
              </button>
            ) : (
              <span
                style={{
                  display: "inline-flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span style={{ fontSize: 14, color: p.muted }}>
                  Reset your sound and display preferences?
                </span>
                <button type="button" onClick={resetAll} style={s.quietBtn}>
                  Clear
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmReset(false)}
                  style={s.textBtn}
                >
                  Keep
                </button>
              </span>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
