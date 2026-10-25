import unittest
from audio.alerts import AlertEngine
from audio.events import make_event
from hardware.oled_client import INIT, SSD1306, Follower, gallery_frames


class FakeBus:
    def __init__(self):
        self.writes = []

    def write_i2c_block_data(self, address, control, data):
        assert len(data) <= 32
        self.writes.append((address, control, list(data)))


class OledClientTests(unittest.TestCase):
    def test_driver_initializes_orientation_and_streams_full_frame(self):
        bus = FakeBus()
        driver = SSD1306(bus, flip_x=True)
        commands = [b for _, control, data in bus.writes if control == 0x00 for b in data]
        self.assertEqual(commands[:len(INIT)], INIT)
        self.assertIn(0xA0, commands)  # mirrored segment remap for a combiner
        self.assertEqual(commands[-1], 0xAF)
        bus.writes.clear()
        driver.show(bytes(range(256)) * 4)
        data = [b for _, control, chunk in bus.writes if control == 0x40 for b in chunk]
        self.assertEqual(data, list(bytes(range(256)) * 4))
        with self.assertRaises(ValueError):
            driver.show(b'short')

    def test_follower_tracks_backend_and_clears_on_disconnect(self):
        now = [0.0]
        engine = AlertEngine()
        follower = Follower(clock=lambda: now[0], failures_before_clear=2)
        self.assertTrue(follower.receive(engine.presentation(0)))
        self.assertIsNotNone(follower.frame())  # initial blank frame is drawn once
        self.assertIsNone(follower.frame())
        engine.add(make_event('knock', .9, 'replay'), 0)
        follower.receive(engine.presentation(0))
        self.assertTrue(any(follower.frame().buffer))
        self.assertFalse(follower.receive(engine.presentation(100)))  # re-poll, same sequence
        self.assertIsNone(follower.frame())
        self.assertFalse(follower.failed())
        self.assertTrue(follower.failed())
        self.assertFalse(any(follower.frame().buffer))
        # Receiver restarted with a new session: old cue is never resurrected.
        fresh = AlertEngine()
        follower.receive(fresh.presentation(0))
        self.assertIsNone(follower.state.active)

    def test_backend_expiry_reaches_the_glasses_without_a_new_packet(self):
        now = [0.0]
        engine = AlertEngine()
        follower = Follower(clock=lambda: now[0])
        engine.add(make_event('smoke_alarm', .9, 'replay'), 0)
        follower.receive(engine.presentation(0))
        self.assertTrue(any(follower.frame().buffer))
        now[0] = 30.0
        self.assertFalse(any(follower.frame().buffer))


class GalleryTests(unittest.TestCase):
    def test_gallery_covers_every_cue_tier_and_arrow_with_distinct_frames(self):
        frames = list(gallery_frames())
        names = [d for d, _ in frames]
        self.assertEqual(sum(d.startswith('icon ') for d in names), 50)
        self.assertEqual(sum(d.startswith('tier ') for d in names), 4)
        self.assertEqual(sum(d.startswith('arrow ') for d in names), 16)
        self.assertEqual(len({bytes(b.buffer) for _, b in frames}), len(frames))

    def test_contrast_is_sent_and_clamped(self):
        bus = FakeBus()
        SSD1306(bus, contrast=999)
        commands = [b for _, control, data in bus.writes if control == 0x00 for b in data]
        index = commands.index(0x81, len(INIT))
        self.assertEqual(commands[index + 1], 255)


if __name__ == '__main__':
    unittest.main()
