import { useMemo, useState } from "react";
import Cue, { SoundIcon } from "./Cue";
import {
  soundCatalog as sounds,
  makeMock,
  tierNames,
  type EventType,
  type Tier,
} from "../lib/events";
import "../preferences.css";
import { mockPriority } from "../lib/presets";

export type Preset = "gentle" | "balanced" | "active";
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
const presets: { id: Preset; name: string; description: string }[] = [
  {
    id: "gentle",
    name: "Less interruption",
    description: "Everyday sounds stay in the background.",
  },
  {
    id: "balanced",
    name: "Balanced",
    description: "Everyday cues, with urgent alerts kept prominent.",
  },
  {
    id: "active",
    name: "More awareness",
    description: "Everyday sounds get a little more attention.",
  },
];
const visibleTiers: Tier[] = [1, 2, 3, 4];
function contrastOnDark(hex: string) {
  const linear = [1, 3, 5].map((start) => {
    const value = parseInt(hex.slice(start, start + 2), 16) / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return (
    (0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2] + 0.05) /
    0.056
  );
}

export default function Preferences({
  overrides,
  onOverridesChange,
  appearance,
  onAppearanceChange,
  preset,
  onPresetChange,
}: {
  overrides: Partial<Record<EventType, Tier>>;
  onOverridesChange: (value: Partial<Record<EventType, Tier>>) => void;
  appearance: Appearance;
  onAppearanceChange: (value: Appearance) => void;
  preset: Preset;
  onPresetChange: (value: Preset) => void;
}) {
  const [query, setQuery] = useState("");
  const [previewType, setPreviewType] = useState<EventType>("knock");
  const previewEvent = useMemo(
    () => ({
      ...makeMock(previewType, mockPriority(previewType, preset, overrides)),
      event_id: "appearance-preview",
    }),
    [previewType, preset, overrides],
  );
  const [announcement, setAnnouncement] = useState("");
  const search = query.trim().toLocaleLowerCase();
  const matches = search
    ? sounds.filter((sound) =>
        `${sound.label} ${sound.detail} ${sound.type.replaceAll("_", " ")}`
          .toLocaleLowerCase()
          .includes(search),
      )
    : [];
  const exceptions = sounds.filter(
    (sound) => overrides[sound.type] !== undefined,
  );
  const lowContrast = visibleTiers.filter(
    (tier) => contrastOnDark(appearance.colors[tier]) < 4.5,
  );
  const remove = (type: EventType) => {
    const next = { ...overrides };
    delete next[type];
    onOverridesChange(next);
  };
  return (
    <div className="attention-settings">
      <section
        className="attention-section"
        aria-labelledby="attention-defaults"
      >
        <div className="attention-heading">
          <h2 id="attention-defaults">Start with a good default.</h2>
          <p>
            Choose how much comes through. Only customize the sounds you want to
            treat differently.
          </p>
        </div>
        <fieldset className="attention-presets">
          <legend className="attention-sr-only">Default attention level</legend>
          {presets.map((item) => (
            <label
              key={item.id}
              className={`attention-preset ${preset === item.id ? "is-selected" : ""}`}
            >
              <input
                type="radio"
                name="attention-preset"
                checked={preset === item.id}
                onChange={() => onPresetChange(item.id)}
              />
              <span>
                <strong>{item.name}</strong>
                <span>{item.description}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <p className="attention-note">
          Browser simulation only. Choices are not saved to a profile or applied
          to the Python receiver yet.
        </p>
      </section>

      <section
        className="attention-section"
        aria-labelledby="attention-exceptions"
      >
        <div className="attention-heading attention-heading-row">
          <div>
            <h2 id="attention-exceptions">Make it yours</h2>
            <p>
              Search for a sound to add an exception. Everything else follows
              your default.
            </p>
          </div>
          {exceptions.length > 0 && (
            <button
              className="attention-text-button"
              onClick={() => {
                onOverridesChange({});
                setAnnouncement("All exceptions removed.");
              }}
            >
              Reset exceptions
            </button>
          )}
        </div>
        <label className="attention-search-label" htmlFor="sound-search">
          Find a sound
        </label>
        <input
          className="attention-search"
          id="sound-search"
          type="search"
          placeholder="Try dog, door, bell…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-describedby="sound-search-help"
        />
        <p className="attention-note" id="sound-search-help">
          Search this demo’s sound catalog. New sound categories need
          recognition support; typing a name does not train a model.
        </p>
        {search && (
          <div
            className="attention-search-results"
            aria-label="Matching sounds"
          >
            {matches.length ? (
              matches.map((sound) => (
                <div className="attention-search-result" key={sound.type}>
                  <SoundIcon type={sound.type} size={19} />
                  <span>
                    <strong>{sound.label}</strong>
                    <span>
                      {sound.receiver
                        ? "Environmental recognition"
                        : "Simulator only · recognition not connected"}
                    </span>
                  </span>
                  <button
                    className="attention-small-button"
                    disabled={overrides[sound.type] !== undefined}
                    onClick={() => {
                      onOverridesChange({
                        ...overrides,
                        [sound.type]: sound.tier,
                      });
                      setQuery("");
                      setAnnouncement(`${sound.label} added to exceptions.`);
                    }}
                  >
                    {overrides[sound.type] !== undefined
                      ? "Added"
                      : "Customize"}
                  </button>
                </div>
              ))
            ) : (
              <p className="attention-empty">
                No matching sounds in this demo. Niche sounds need model support
                before they can trigger alerts.
              </p>
            )}
          </div>
        )}
        <div className="attention-exceptions">
          {exceptions.length === 0 ? (
            <p className="attention-empty">
              No exceptions yet. Your default handles the details.
            </p>
          ) : (
            exceptions.map((sound) => (
              <div className="attention-exception" key={sound.type}>
                <SoundIcon type={sound.type} size={19} />
                <span className="attention-sound-name">
                  <strong>{sound.label}</strong>
                  {!sound.receiver && <span>Simulator only</span>}
                </span>
                <label className="attention-tier-select">
                  <span className="attention-sr-only">
                    {sound.label} priority
                  </span>
                  <select
                    value={overrides[sound.type]}
                    onChange={(event) =>
                      onOverridesChange({
                        ...overrides,
                        [sound.type]: Number(event.target.value) as Tier,
                      })
                    }
                  >
                    {tierNames.map((name, tier) => (
                      <option value={tier} key={tier}>
                        {tier} · {name}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="attention-text-button"
                  onClick={() => {
                    remove(sound.type);
                    setAnnouncement(
                      `${sound.label} follows your default again.`,
                    );
                  }}
                  aria-label={`Remove ${sound.label} exception`}
                >
                  Remove
                </button>
              </div>
            ))
          )}
        </div>
        <p className="attention-sr-only" role="status">
          {announcement}
        </p>
      </section>

      <details className="attention-display">
        <summary>Display preview</summary>
        <p className="attention-note">
          Keep ordinary cues quick to recognize. Urgent cues always include a
          short label. These controls change the browser preview, not connected
          hardware.
        </p>
        <div
          className="attention-preview-stage"
          aria-label="Simulated cue design preview"
        >
          <Cue
            event={previewEvent}
            appearance={appearance}
            direction={appearance.direction}
          />
        </div>
        <div className="attention-display-fields">
          <label>
            Preview sound
            <select
              value={previewType}
              onChange={(e) => setPreviewType(e.target.value as EventType)}
            >
              {sounds.map((sound) => (
                <option key={sound.type} value={sound.type}>
                  {sound.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Cue text
            <select
              value={appearance.text}
              onChange={(event) =>
                onAppearanceChange({
                  ...appearance,
                  text: event.target.value as Appearance["text"],
                })
              }
            >
              <option value="icons">Icons · text for urgent cues</option>
              <option value="labels">Icons and short labels</option>
            </select>
          </label>
          <label>
            Motion
            <select
              value={appearance.motion}
              onChange={(event) =>
                onAppearanceChange({
                  ...appearance,
                  motion: event.target.value as Appearance["motion"],
                })
              }
            >
              <option value="none">Still</option>
              <option value="gentle">Brief gentle pulse</option>
            </select>
          </label>
          <label>
            Simulated direction
            <select
              value={appearance.direction}
              onChange={(event) =>
                onAppearanceChange({
                  ...appearance,
                  direction: event.target.value as Appearance["direction"],
                })
              }
            >
              <option value="unknown">Unknown · no direction cue</option>
              <option value="left">Left</option>
              <option value="right">Right</option>
              <option value="front">Front</option>
              <option value="behind">Behind</option>
            </select>
          </label>
        </div>
        <p className="attention-note">
          Direction is a labeled simulation. Live direction remains unknown
          until synchronized microphones and localization are validated.
        </p>
        <fieldset className="attention-colors">
          <legend>Browser cue colors</legend>
          {visibleTiers.map((tier) => (
            <label key={tier}>
              <input
                type="color"
                value={appearance.colors[tier]}
                onChange={(event) =>
                  onAppearanceChange({
                    ...appearance,
                    colors: {
                      ...appearance.colors,
                      [tier]: event.target.value,
                    },
                  })
                }
              />
              <span>{tierNames[tier]}</span>
            </label>
          ))}
        </fieldset>
        <p className="attention-note">
          The physical SSD1306 display is white and black, so color is
          browser-only. Keep high contrast; icons and urgency should remain
          understandable without color.
        </p>
        {lowContrast.length > 0 && (
          <p className="attention-contrast-warning" role="status">
            Low contrast on the dark preview:{" "}
            {lowContrast.map((tier) => tierNames[tier]).join(", ")}. A lighter
            cue color will be easier to see.
          </p>
        )}
        <button
          className="attention-text-button"
          onClick={() =>
            onAppearanceChange({
              ...defaultAppearance,
              colors: { ...defaultAppearance.colors },
            })
          }
        >
          Reset display preview
        </button>
      </details>
    </div>
  );
}
