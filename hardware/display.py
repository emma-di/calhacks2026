"""Dependency-free 128x64 monochrome renderer and transport-independent display state."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import time

WIDTH, HEIGHT = 128, 64


# Original 5x7 bitmap alphabet and 24x24 line icons, shared with the browser preview.
# Unknown characters become '?'.
_ASSETS = json.loads((Path(__file__).with_name("oled-assets.json")).read_text())
_GLYPHS = _ASSETS["glyphs"]
ICON_IDS = frozenset(_ASSETS["icons"])
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


def draw_icon(bitmap, icon_id, x, y, size=24):
    """Original line pictograms on a 24x24 logical grid; small variant uses 16px."""
    def line(a, b, c, d):
        bitmap.line(x + round(a * size / 24), y + round(b * size / 24),
                    x + round(c * size / 24), y + round(d * size / 24))

    paths = _ASSETS["icons"]
    for path in paths[icon_id]:
        for start, end in zip(path, path[1:]):
            line(*start, *end)


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

    @classmethod
    def parse(cls, value):
        if not isinstance(value, dict):
            raise ValueError("Presentation must be an object")
        if not set(cls.__dataclass_fields__).issubset(value):
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
        fields = cls.__dataclass_fields__
        return cls(**{key: value[key] for key in fields})


def label_lines(label, width=19):
    # Hard wrapping also bounds a long unbroken word. Two lines, explicit truncation.
    remaining, lines = " ".join(label.upper().split()), []
    while remaining and len(lines) < 2:
        cut = len(remaining) if len(remaining) <= width else remaining.rfind(" ", 0, width + 1)
        if cut <= 0:
            cut = width
        lines.append(remaining[:cut])
        remaining = remaining[cut:].lstrip()
    if remaining:
        lines[-1] = lines[-1][:width - 3].rstrip() + "..."
    return lines


def render(presentation=None, show_labels=True):
    bitmap = Bitmap()
    if presentation is None or presentation.effective_tier == 0 or presentation.remaining_ms == 0:
        return bitmap
    tier = presentation.effective_tier
    if tier == 1:
        draw_icon(bitmap, presentation.icon_id, 8, 42, 16)
        if show_labels:
            bitmap.text(presentation.label.upper()[:14], 34, 48)
        return bitmap
    if tier >= 3:
        bitmap.rect(0, 0, 128, 64)
    if tier == 4:
        bitmap.rect(2, 2, 124, 60)
        bitmap.rect(3, 3, 122, 11, fill=True)
        bitmap.centered("URGENT", 5, value=0)
        icon_y, text_y = 16, 43
    else:
        if tier == 3:
            bitmap.centered("ATTENTION", 4)
        icon_y, text_y = (14, 42) if tier == 3 else (5, 35)
    draw_icon(bitmap, presentation.icon_id, 52, icon_y)
    if show_labels or tier == 4:
        for index, line in enumerate(label_lines(presentation.label)):
            bitmap.centered(line, text_y + 9 * index)
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
              "smoke": "Smoke alarm", "siren": "Siren", "clock": "Alarm clock"}
    payload = json.loads(args.snapshot.read_text()) if args.snapshot else dict(
        schema_version=1, session_id="offline-demo", state_sequence=1, event_id="fake-cue",
        label=labels[args.event], icon_id=args.event, effective_tier=args.tier, remaining_ms=30000)
    cue = Presentation.parse(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(render(cue, show_labels=not args.icons_only).pbm())
    print(f"Wrote 128x64 one-bit design preview: {args.output}")


if __name__ == "__main__":
    main()
