"""Dependency-free 128x64 monochrome renderer and transport-independent display state."""
from __future__ import annotations  # Pi OS Bullseye ships Python 3.9
from dataclasses import dataclass
import json
import math
from pathlib import Path
import time

WIDTH, HEIGHT = 128, 64


# Original 5x7 bitmap alphabet and 32x32 icons (hardware/icons.py), shared with the browser preview.
# Unknown characters become '?'.
_ASSETS = json.loads((Path(__file__).with_name("oled-assets.json")).read_text())
_GLYPHS = _ASSETS["glyphs"]
ICON_IDS = frozenset(_ASSETS["bitmaps"])
DIRECTIONS = ("left", "right", "front", "behind")
FONT = {char: rows.split() for char, rows in _GLYPHS.items()}


class Bitmap:
    """PBM-compatible row-major pixels: MSB first, one means illuminated."""

    def __init__(self):
        self.buffer = bytearray(WIDTH * HEIGHT // 8)

    def pixel(self, x, y, value=1):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            index, bit = y * (WIDTH // 8) + x // 8, 1 << (7 - x % 8)
            if value:
                self.buffer[index] |= bit
            else:
                self.buffer[index] &= 255 ^ bit

    def get(self, x, y):
        return (self.buffer[y * (WIDTH // 8) + x // 8] >> (7 - x % 8)) & 1

    def line(self, x0, y0, x1, y1, value=1):
        dx, sx = abs(x1 - x0), 1 if x0 < x1 else -1
        dy, sy = -abs(y1 - y0), 1 if y0 < y1 else -1
        error = dx + dy
        while True:
            self.pixel(x0, y0, value)
            if x0 == x1 and y0 == y1:
                return
            twice = 2 * error
            if twice >= dy:
                error += dy
                x0 += sx
            if twice <= dx:
                error += dx
                y0 += sy

    def rect(self, x, y, width, height, fill=False):
        if fill:
            for row in range(y, y + height):
                self.line(x, row, x + width - 1, row)
        else:
            self.line(x, y, x + width - 1, y)
            self.line(x, y + height - 1, x + width - 1, y + height - 1)
            self.line(x, y, x, y + height - 1)
            self.line(x + width - 1, y, x + width - 1, y + height - 1)

    def text(self, text, x, y, value=1):
        for char in text.upper():
            for row, pixels in enumerate(FONT.get(char, FONT["?"])):
                for column, pixel in enumerate(pixels):
                    if pixel == "1":
                        self.pixel(x + column, y + row, value)
            x += 6

    def centered(self, text, y, value=1):
        self.text(text, (WIDTH - (len(text) * 6 - 1)) // 2, y, value)

    def pbm(self):
        # PBM one means black; complement so illuminated pixels appear white on black.
        return b"P4\n128 64\n" + bytes(byte ^ 255 for byte in self.buffer)

    def ssd1306_pages(self):
        """Convert to 8 vertical pages; no bus commands or device access."""
        return bytes(sum(self.get(x, page * 8 + bit) << bit for bit in range(8))
                     for page in range(8) for x in range(WIDTH))


ICON_SIZE = 32
EDGE = 6  # gap between a directed cue and its screen edge, room for the tier boxes and edge line


def draw_icon(bitmap, icon_id, x, y):
    for row, bits in enumerate(_ASSETS["bitmaps"][icon_id]):
        for column, bit in enumerate(bits):
            if bit == "1":
                bitmap.pixel(x + column, y + row)


@dataclass(frozen=True)
class Presentation:
    schema_version: int
    session_id: str
    state_sequence: int
    event_id: str | None
    label: str
    icon_id: str | None
    effective_tier: int
    remaining_ms: int
    direction: str | None = None  # left/right/front/behind once localization is measured

    @classmethod
    def parse(cls, value):
        if not isinstance(value, dict):
            raise ValueError("Presentation must be an object")
        if not (set(cls.__dataclass_fields__) - {"direction"}).issubset(value):
            raise ValueError("Presentation is missing required fields")
        if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
            raise ValueError("Expected presentation schema_version 1")
        for key in ("state_sequence", "effective_tier", "remaining_ms"):
            if type(value.get(key)) is not int or value[key] < 0:
                raise ValueError(f"{key} must be a nonnegative integer")
        if value["effective_tier"] > 4:
            raise ValueError("effective_tier must be 0..4")
        if not isinstance(value.get("session_id"), str) or not 0 < len(value["session_id"]) <= 128:
            raise ValueError("Expected bounded session_id")
        if not isinstance(value.get("label"), str) or len(value["label"]) > 128:
            raise ValueError("Expected label of at most 128 characters")
        event_id, icon_id = value.get("event_id"), value.get("icon_id")
        if event_id is not None and (not isinstance(event_id, str) or not 0 < len(event_id) <= 128):
            raise ValueError("Invalid event_id")
        if icon_id is not None and (not isinstance(icon_id, str) or icon_id not in ICON_IDS):
            raise ValueError("Unknown icon_id")
        if value["effective_tier"] > 0 and (event_id is None or icon_id is None or not value["label"].strip()):
            raise ValueError("Visible cue needs event_id, icon_id and label")
        direction = value.get("direction")
        if direction not in (None, *DIRECTIONS):
            raise ValueError("direction must be left, right, front, behind or null")
        fields = [key for key in cls.__dataclass_fields__ if key != "direction"]
        return cls(**{key: value[key] for key in fields}, direction=direction)


def fit_label(label, width):
    text = " ".join(label.upper().split())
    return text if len(text) <= width else text[:width - 3].rstrip() + "..."


# Icon top-left for each placement, and the row its label uses. The label row is always reserved,
# so the icon never moves when labels are switched on or off.
# The entire panel sits on the right side of the wearer's field of view. The icon stays
# centered within that patch; a solid triangle on that side shows the sound's direction.
def layout(direction, label):
    x, y, text_y = (WIDTH - ICON_SIZE) // 2, 10, 55
    text = fit_label(label, 19) if label else None
    tw = len(text) * 6 - 1 if text else 0
    return dict(box=(x, y, ICON_SIZE, ICON_SIZE), icon=(x, y), text=text,
                origin=((WIDTH - tw) // 2, text_y) if text else None, width=tw)


def draw_edge(bitmap, direction):
    """Solid triangle beside the stationary icon, pointing toward the sound; none for unknown.

    Filled shapes read better than line arrows on a 128x64 panel seen through optics.
    """
    if direction in ("left", "right"):
        for k in range(-6, 7):                      # 7 px deep, 13 px tall, apex outward
            for x in range(30 + abs(k), 37):
                bitmap.pixel(x if direction == "left" else WIDTH - 1 - x, 26 + k)
    elif direction == "front":
        for row in range(6):                        # apex at the top edge
            for x in range(64 - row, 65 + row):
                bitmap.pixel(x, row)
    elif direction == "behind":
        for row in range(6):                        # apex pointing down, above the label row
            for x in range(64 - row, 65 + row):
                bitmap.pixel(x, 53 - row)


def render(presentation=None, show_labels=True):
    """Tier changes only the box around the cue: 1 none, 2 thin, 3 double, 4 double plus an
    inverted label (Urgent always shows its label). The icon is centered; direction is shown by a solid triangle.
    """
    bitmap = Bitmap()
    if presentation is None or presentation.effective_tier == 0 or presentation.remaining_ms == 0:
        return bitmap
    tier, direction = presentation.effective_tier, presentation.direction
    place = layout(direction, presentation.label if show_labels or tier == 4 else None)
    x, y, cw, ch = place["box"]
    if tier >= 2:
        bitmap.rect(x - 2, y - 2, cw + 4, ch + 4)
    if tier >= 3:
        bitmap.rect(x - 4, y - 4, cw + 8, ch + 8)
    draw_icon(bitmap, presentation.icon_id, *place["icon"])
    if place["text"]:
        tx, ty = place["origin"]
        if tier == 4:
            bitmap.rect(tx - 2, ty - 2, place["width"] + 4, 11, fill=True)
        bitmap.text(place["text"], tx, ty, value=0 if tier == 4 else 1)
    draw_edge(bitmap, direction)
    return bitmap


class DisplayState:
    """Consumer guard; backend still chooses priority. Call tick even without packets."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.connected = False
        self.session_id = None
        self.sequence = -1
        self.active = None
        self.deadline = 0.0

    def connect(self, session_id):
        if not isinstance(session_id, str) or not 0 < len(session_id) <= 128:
            raise ValueError("Invalid session_id")
        self.active, self.deadline = None, 0.0
        if session_id != self.session_id:
            self.sequence = -1
        self.session_id, self.connected = session_id, True

    def disconnect(self):
        self.connected = False
        self.active, self.deadline = None, 0.0

    def accept(self, snapshot):
        cue = Presentation.parse(snapshot)
        if not self.connected or cue.session_id != self.session_id or cue.state_sequence <= self.sequence:
            return False
        now = self.clock()
        if not math.isfinite(now):
            raise ValueError("Clock must be finite")
        self.tick(now)
        self.sequence = cue.state_sequence
        if cue.effective_tier == 0 or cue.remaining_ms == 0:
            self.active, self.deadline = None, 0.0
            return True
        # The backend bumps state_sequence only when the cue really changes (new cue, resume after
        # an interruption, an ongoing urgent sound extending its lifetime, clear). Re-polled
        # snapshots repeat their sequence and are rejected above, so they can never extend a cue.
        self.active, self.deadline = cue, now + min(cue.remaining_ms, 30000) / 1000
        return True

    def tick(self, now=None):
        now = self.clock() if now is None else now
        if self.active and now >= self.deadline:
            self.active, self.deadline = None, 0.0
        return self.active

    def frame(self):
        return render(self.tick())


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Render a fake cue or presentation JSON to PBM; no device access")
    parser.add_argument("--event", choices=sorted(ICON_IDS), default="knock")
    parser.add_argument("--tier", type=int, choices=range(5), default=2)
    parser.add_argument("--snapshot", type=Path, help="Read a presentation snapshot instead of fake input")
    parser.add_argument("--icons-only", action="store_true", help="Hide nonurgent event labels; urgent text remains")
    parser.add_argument("--output", type=Path, default=Path(".cache/display-preview.pbm"))
    args = parser.parse_args()
    labels = {"knock": "Door knock", "bell": "Bell / chime", "dog": "Dog barking", "name": "Your name",
              "smoke": "Smoke alarm", "siren": "Siren", "clock": "Alarm clock", "chat": "Conversation"}
    payload = json.loads(args.snapshot.read_text()) if args.snapshot else dict(
        schema_version=1, session_id="offline-demo", state_sequence=1, event_id="fake-cue",
        label=labels[args.event], icon_id=args.event, effective_tier=args.tier, remaining_ms=30000)
    cue = Presentation.parse(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(render(cue, show_labels=not args.icons_only).pbm())
    print(f"Wrote 128x64 one-bit design preview: {args.output}")


if __name__ == "__main__":
    main()
