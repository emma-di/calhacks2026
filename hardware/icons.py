"""Source of the 32x32 one-bit cue icons. Regenerate: python3 -m hardware.icons

Icons are built from simple shapes so they stay tidy, then baked into hardware/oled-assets.json
("bitmaps"), which both the Python renderer and the browser read. Style: rounded, 2px strokes so they
survive the optics, small friendly details (eyes, sparkles, motion marks).
"""
import json
import math
from pathlib import Path

SIZE = 32
ASSETS = Path(__file__).with_name("oled-assets.json")


class Canvas:
    def __init__(self):
        self.px = [[0] * SIZE for _ in range(SIZE)]

    def set(self, x, y, v=1):
        if 0 <= x < SIZE and 0 <= y < SIZE:
            self.px[y][x] = v

    def ellipse(self, cx, cy, rx, ry, v=1):
        for y in range(SIZE):
            for x in range(SIZE):
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                    self.set(x, y, v)

    def ring(self, cx, cy, rx, ry, t=2):
        self.ellipse(cx, cy, rx, ry)
        self.ellipse(cx, cy, rx - t, ry - t, 0)

    def rect(self, x0, y0, x1, y1, v=1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, v)

    def round_rect(self, x0, y0, x1, y1, r, v=1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                dx = max(x0 + r - x - 0.5, 0, x + 0.5 - (x1 + 1 - r))
                dy = max(y0 + r - y - 0.5, 0, y + 0.5 - (y1 + 1 - r))
                if dx * dx + dy * dy <= r * r:
                    self.set(x, y, v)

    def round_frame(self, x0, y0, x1, y1, r, t=2):
        self.round_rect(x0, y0, x1, y1, r)
        self.round_rect(x0 + t, y0 + t, x1 - t, y1 - t, max(r - t, 0), 0)

    def arc(self, cx, cy, r, start, end, t=2):
        """Thick arc, angles in degrees, 0 = right, 90 = down."""
        for y in range(SIZE):
            for x in range(SIZE):
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                d = math.hypot(dx, dy)
                a = math.degrees(math.atan2(dy, dx)) % 360
                inside = (start <= a <= end) if start <= end else (a >= start or a <= end)
                if r - t <= d <= r and inside:
                    self.set(x, y)

    def polygon(self, points, v=1):
        for y in range(SIZE):
            for x in range(SIZE):
                px, py, inside = x + 0.5, y + 0.5, False
                for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
                    if (y0 > py) != (y1 > py) and px < (x1 - x0) * (py - y0) / (y1 - y0) + x0:
                        inside = not inside
                if inside:
                    self.set(x, y, v)

    def rows(self):
        return ["".join("1" if v else "0" for v in row) for row in self.px]


def dog():
    c = Canvas()
    c.ring(16, 17.5, 10.5, 10, 2)                       # head
    c.ellipse(5.5, 13, 3.5, 7)                          # floppy ears
    c.ellipse(26.5, 13, 3.5, 7)
    c.ellipse(12, 16, 1.6, 2)                           # eyes
    c.ellipse(20, 16, 1.6, 2)
    c.ellipse(16, 20.5, 2.6, 1.8)                       # nose
    c.set(15, 23); c.set(16, 23); c.set(14, 24); c.set(17, 24)
    c.ellipse(16, 25.5, 1.6, 1.6)                       # tongue
    return c


def knock():
    c = Canvas()
    c.round_frame(4, 3, 19, 29, 3)                      # door
    c.ellipse(15.5, 17, 1.6, 1.6)                       # knob
    c.rect(2, 29, 21, 30)                               # step
    for cy in (9, 16, 23):                              # knock marks
        c.arc(21, cy, 6, 330, 30, 2)
    c.arc(21, 16, 10, 335, 25, 2)
    return c


def bell():
    c = Canvas()
    shape = [(16, 5), (21, 7), (23, 12), (23, 19), (27, 24), (5, 24), (9, 19), (9, 12), (11, 7)]
    c.polygon(shape)
    inner = [(16, 7.5), (19.8, 9), (21, 13), (21, 20), (23.2, 22), (8.8, 22), (11, 20), (11, 13), (12.2, 9)]
    c.polygon(inner, 0)
    c.ellipse(16, 4, 2, 2)                              # hanger
    c.ellipse(16, 27, 2.5, 2.2)                         # clapper
    for sx, sy in ((4, 6), (28, 9)):                    # sparkles
        c.set(sx, sy - 2); c.set(sx, sy - 1); c.set(sx, sy + 1); c.set(sx, sy + 2)
        c.set(sx - 2, sy); c.set(sx - 1, sy); c.set(sx + 1, sy); c.set(sx + 2, sy); c.set(sx, sy)
    return c


def name():
    c = Canvas()
    c.ring(14, 14, 10, 10, 2)                           # face
    c.ellipse(10.5, 12.5, 1.5, 2)                       # eyes
    c.ellipse(17.5, 12.5, 1.5, 2)
    c.arc(14, 15, 4.5, 25, 155, 2)                      # smile
    c.round_rect(19, 19, 30, 28, 3)                     # speech bubble: someone said your name
    c.round_rect(21, 21, 28, 26, 1, 0)
    c.polygon([(21, 27), (24, 27), (20, 31)])
    c.rect(24, 22, 25, 23)                              # "!" inside the bubble
    c.set(24, 25); c.set(25, 25)
    return c


def smoke():
    c = Canvas()
    c.ellipse(16, 20.5, 9, 9)                           # flame: teardrop outline
    c.polygon([(16, 2), (7.6, 18), (24.4, 18)])
    c.ellipse(16, 20.5, 7, 7, 0)
    c.polygon([(16, 6.5), (9.6, 19), (22.4, 19)], 0)
    c.ellipse(16, 23.5, 3.2, 3.2)                       # inner flame
    c.polygon([(16, 14), (13, 22.5), (19, 22.5)])
    return c


def siren():
    c = Canvas()
    c.round_rect(8, 10, 23, 26, 7)                      # dome
    c.rect(8, 19, 23, 26)
    c.round_rect(11, 13, 20, 25, 4, 0)
    c.rect(11, 19, 20, 25, 0)
    c.rect(14, 15, 15, 21)                              # shine
    c.rect(5, 26, 26, 29)                               # base
    c.rect(15, 3, 16, 6)                                # rays
    c.rect(3, 13, 5, 14)
    c.rect(26, 13, 28, 14)
    for i in range(3):
        c.set(6 + i, 6 + i); c.set(7 + i, 6 + i)
        c.set(25 - i, 6 + i); c.set(24 - i, 6 + i)
    return c


def clock():
    c = Canvas()
    c.ring(16, 18, 10, 10, 2)                           # face
    c.ellipse(7, 7, 3.5, 3.5)                           # bells
    c.ellipse(25, 7, 3.5, 3.5)
    c.rect(15, 11, 16, 18)                              # hands
    c.rect(16, 17, 21, 18)
    c.rect(8, 27, 10, 29)                               # feet
    c.rect(21, 27, 23, 29)
    c.rect(15, 5, 16, 7)                                # top button
    return c


def conversation():
    c = Canvas()
    c.round_frame(2, 4, 21, 18, 5)
    c.polygon([(6, 17), (10, 17), (5, 23)])
    c.round_rect(12, 13, 29, 26, 5)
    c.round_rect(14, 15, 27, 24, 3, 0)
    c.polygon([(23, 25), (27, 25), (28, 30)])
    for x in (17, 20, 23):
        c.ellipse(x + 0.5, 19.5, 1.2, 1.2)
    return c


def check():
    c = Canvas()
    c.ring(16, 16, 13, 13, 2)                           # a calm done mark
    c.polygon([(8, 16), (11, 13), (14, 17), (22, 9), (25, 12), (14, 23)])
    return c


ICONS = dict(dog=dog, knock=knock, bell=bell, name=name, smoke=smoke, siren=siren, clock=clock,
             chat=conversation, check=check)


def build():
    assets = json.loads(ASSETS.read_text())
    assets.pop("icons", None)
    assets["note"] = ("Shared by hardware/display.py and frontend/src/lib/oled.ts. 5x7 glyph rows and 32x32 "
                      "icon bitmaps (generated by hardware/icons.py).")
    assets["bitmaps"] = {key: make().rows() for key, make in ICONS.items()}
    ASSETS.write_text(json.dumps(assets, indent=1) + "\n")


if __name__ == "__main__":
    build()
    for key, make in ICONS.items():
        print(key)
        for row in make().rows():
            print(row.replace("0", "·").replace("1", "█"))
