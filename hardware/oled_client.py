"""Glasses-side loop: poll the receiver's /display envelope and drive a 128x64 SSD1306.

Run on the Pi (or any machine) once the laptop receiver listens on the network:

  laptop:  python3 -m audio.server --host 0.0.0.0
  Pi:      python3 -m hardware.oled_client --receiver http://LAPTOP_IP:8765 --sink ssd1306
  no OLED: python3 -m hardware.oled_client --sink ascii          # draws frames in the terminal
  wiring:  python3 -m hardware.oled_client --sink ssd1306 --self-test   # fake cues, no network

The backend owns priority and timing; DisplayState only enforces expiry, staleness and clearing
on disconnect. Only `--sink ssd1306` touches hardware and it needs `pip install smbus2`.
"""
import argparse
import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from hardware.display import HEIGHT, WIDTH, DisplayState, render

# Standard SSD1306 128x64 init: charge pump on, horizontal addressing, full contrast.
INIT = [0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0x8D, 0x14, 0x20, 0x00,
        0xDA, 0x12, 0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6]


class SSD1306:
    """Minimal I2C driver. `bus` is any object with smbus2's write_i2c_block_data."""

    def __init__(self, bus, address=0x3C, flip_x=False, flip_y=False, contrast=None):
        self.bus, self.address = bus, address
        # Segment remap / COM scan direction; a beam-splitter combiner usually needs one axis mirrored.
        orientation = [0xA0 if flip_x else 0xA1, 0xC0 if flip_y else 0xC8]
        brightness = [] if contrast is None else [0x81, max(0, min(255, int(contrast)))]
        self.command(*INIT, *orientation, *brightness, 0xAF)

    def command(self, *values):
        for start in range(0, len(values), 16):
            self.bus.write_i2c_block_data(self.address, 0x00, list(values[start:start + 16]))

    def show(self, pages):
        if len(pages) != WIDTH * HEIGHT // 8:
            raise ValueError('Expected 1024 page bytes')
        self.command(0x21, 0, WIDTH - 1, 0x22, 0, HEIGHT // 8 - 1)
        for start in range(0, len(pages), 16):
            self.bus.write_i2c_block_data(self.address, 0x40, list(pages[start:start + 16]))

    def off(self):
        self.command(0xAE)


class AsciiSink:
    def __init__(self, stream=sys.stdout):
        self.stream = stream

    def show(self, bitmap):
        rows = []
        for y in range(0, HEIGHT, 2):
            rows.append(''.join('█' if bitmap.get(x, y) or bitmap.get(x, y + 1) else '·'
                                for x in range(0, WIDTH, 1)))
        self.stream.write('\x1b[H\x1b[2J' + '\n'.join(rows) + '\n')
        self.stream.flush()


def make_sink(name, args):
    if name == 'ssd1306':
        try:
            from smbus2 import SMBus
        except ImportError:
            raise SystemExit('smbus2 is missing: pip install smbus2 (and enable I2C with raspi-config)')
        driver = SSD1306(SMBus(args.bus), int(args.address, 16), args.flip_x, args.flip_y,
                         getattr(args, 'contrast', None))
        # On exit leave the panel on (the last frame drawn is blank): another program, such as the
        # DETECT bear demo service, may share this display and should not find it switched off.
        return lambda bitmap: driver.show(bitmap.ssd1306_pages()), (lambda: None)
    if name == 'ascii':
        sink = AsciiSink()
        return sink.show, lambda: None
    if name == 'pbm':
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)

        def write(bitmap):
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(bitmap.pbm())
            temporary.replace(path)
        return write, lambda: None
    return (lambda bitmap: None), (lambda: None)


class Follower:
    """Turns a stream of poll results into frames. Separated from I/O for tests."""

    def __init__(self, clock=time.monotonic, failures_before_clear=3):
        self.state = DisplayState(clock=clock)
        self.failures = 0
        self.failures_before_clear = failures_before_clear
        self.show_labels = False
        self.last_frame = None
        self.last_event_id = None

    def receive(self, envelope):
        self.failures = 0
        if envelope['session_id'] != self.state.session_id or not self.state.connected:
            self.state.connect(envelope['session_id'])  # a new backend run never inherits old cues
        self.show_labels = bool(envelope.get('show_labels', False))
        return self.state.accept(envelope)

    def failed(self):
        self.failures += 1
        if self.failures >= self.failures_before_clear and self.state.connected:
            self.state.disconnect()  # never leave a stale cue on the glasses
            return True
        return False

    def frame(self):
        """Return a bitmap only when the pixels changed."""
        bitmap = render(self.state.tick(), show_labels=self.show_labels)
        if bytes(bitmap.buffer) == self.last_frame:
            return None
        self.last_frame = bytes(bitmap.buffer)
        return bitmap


def self_test(show, labels):
    """HW-03: fake cues straight to the display, independent of recognition and network."""
    from hardware.display import Presentation
    cues = [('knock', 'Door knock', 2), ('dog', 'Dog barking', 1), ('name', 'Your name', 3),
            ('smoke', 'Smoke alarm', 4), ('siren', 'Siren', 3), ('clock', 'Alarm clock', 2)]
    for index, (icon, label, tier) in enumerate(cues, 1):
        cue = Presentation.parse(dict(schema_version=1, session_id='self-test', state_sequence=index,
                                      event_id=f'self-test-{index}', label=label, icon_id=icon,
                                      effective_tier=tier, remaining_ms=2500))
        print(f'self-test: {label} (tier {tier})', flush=True)
        show(render(cue, show_labels=labels))
        time.sleep(2.5)
    show(render(None))
    print('self-test: cleared', flush=True)


def gallery_frames(labels=True):
    """Optics review: every cue icon (tier 2), the four tier treatments, then all 16 arrow positions.

    Yields (description, bitmap). Uses only the deployed icon file, so it runs on the Pi as is.
    """
    from hardware.display import ICON_IDS, Presentation
    def frame(icon, label, tier=2, bearing=None, show=labels):
        value = dict(schema_version=1, session_id='gallery', state_sequence=1, event_id='gallery',
                     label=label, icon_id=icon, effective_tier=tier, remaining_ms=2000)
        if bearing is not None:
            side = 'front' if -45 <= bearing <= 45 else 'right' if 45 < bearing <= 135 else \
                'left' if -135 <= bearing < -45 else 'behind'
            value.update(direction=side, bearing_degrees=bearing)
        return render(Presentation.parse(value), show_labels=show)
    for icon in sorted(i for i in ICON_IDS if i.startswith('cue_')):
        name = icon[4:].replace('_', ' ')
        yield f'icon {name}', frame(icon, name)
    for tier, name in ((1, 'Ambient'), (2, 'Notify'), (3, 'Attention'), (4, 'Urgent')):
        yield f'tier {tier} {name}', frame('cue_doorbell', name, tier)
    for k in range(16):
        bearing = k * 22.5 - 180
        yield f'arrow {bearing:+.1f} deg', frame('cue_doorbell', 'doorbell', 2, bearing, False)


def main():
    parser = argparse.ArgumentParser(description='Follow the receiver and drive the glasses display')
    parser.add_argument('--receiver', default='http://127.0.0.1:8765')
    parser.add_argument('--sink', choices=['ssd1306', 'ascii', 'pbm', 'none'], default='ascii')
    parser.add_argument('--client', default='oled', help='Name reported to the companion as connected display')
    parser.add_argument('--interval', type=float, default=0.1, help='Poll interval in seconds')
    parser.add_argument('--bus', type=int, default=1)
    parser.add_argument('--address', default='3C', help='I2C address in hex')
    parser.add_argument('--flip-x', action='store_true', help='Mirror horizontally (combiner reflection)')
    parser.add_argument('--flip-y', action='store_true', help='Mirror vertically (display mounted upside down)')
    parser.add_argument('--output', default='.cache/oled-live.pbm', help='PBM sink path')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--gallery', action='store_true',
                        help='Optics review: all cue icons, tier treatments and 16 arrow positions')
    parser.add_argument('--gallery-seconds', type=float, default=2.0, help='Seconds per gallery frame')
    parser.add_argument('--contrast', type=int, help='SSD1306 brightness 0-255 (default: init value 0xCF)')
    parser.add_argument('--labels', action='store_true', help='Self-test only: show nonurgent labels')
    args = parser.parse_args()
    show, close = make_sink(args.sink, args)
    if args.self_test:
        try:
            self_test(show, args.labels)
        finally:
            close()
        return
    if args.gallery:
        try:
            frames = list(gallery_frames(labels=True))
            for index, (description, bitmap) in enumerate(frames, 1):
                print(f'gallery {index}/{len(frames)}: {description}', flush=True)
                show(bitmap)
                time.sleep(args.gallery_seconds)
            show(render(None))
        finally:
            close()
        return
    follower = Follower()
    url = f"{args.receiver.rstrip('/')}/display?client={args.client}"
    print(f'Following {url} -> {args.sink}', file=sys.stderr, flush=True)
    show(render(None))
    try:
        while True:
            started = time.monotonic()
            try:
                with urlopen(url, timeout=1) as response:
                    envelope = json.loads(response.read())
                if follower.receive(envelope) and envelope.get('event_id') and envelope['event_id'] != follower.last_event_id:
                    follower.last_event_id = envelope['event_id']
                    rtt = (time.monotonic() - started) * 1000
                    print(f"cue {envelope['label']!r} tier {envelope['effective_tier']} seq {envelope['state_sequence']}:"
                          f" ~{envelope.get('age_ms', 0) + rtt / 2:.0f} ms after the receiver accepted it",
                          file=sys.stderr, flush=True)
            except (OSError, ValueError, KeyError) as exc:
                if follower.failed():
                    print(f'receiver unreachable ({exc}); display cleared', file=sys.stderr, flush=True)
            bitmap = follower.frame()
            if bitmap is not None:
                show(bitmap)
            time.sleep(max(0.0, args.interval - (time.monotonic() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        show(render(None))
        close()


if __name__ == '__main__':
    main()
