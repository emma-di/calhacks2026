"""Offline display invariants; no NumPy, network, model, or device required."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from hardware.display import Bitmap, DisplayState, Presentation, render


def snapshot(**changes):
    value = dict(schema_version=1, session_id="run-a", state_sequence=1,
                 event_id="event-a", label="Door knock", icon_id="knock",
                 effective_tier=2, remaining_ms=3000)
    value.update(changes)
    return value


class DisplayTests(unittest.TestCase):
    def test_bitmap_dimensions_binary_pixels_and_pbm(self):
        frame = render(Presentation.parse(snapshot()))
        self.assertEqual(len(frame.buffer), 1024)
        self.assertEqual({frame.get(x, y) for y in range(64) for x in range(128)}, {0, 1})
        self.assertEqual(frame.pbm()[:10], b"P4\n128 64\n")
        self.assertEqual(len(frame.pbm()), 1034)
        # PBM black-background preview is inverted, but hardware RAM uses illuminated=1.
        self.assertEqual(Bitmap().pbm()[10:], bytes([255]) * 1024)

    def test_ssd1306_pages_map_vertical_bits(self):
        frame = Bitmap()
        frame.pixel(3, 0)
        frame.pixel(3, 7)
        frame.pixel(127, 63)
        pages = frame.ssd1306_pages()
        self.assertEqual(len(pages), 1024)
        self.assertEqual(pages[3], 0b10000001)
        self.assertEqual(pages[-1], 0b10000000)
        self.assertEqual(sum(byte.bit_count() for byte in pages), 3)

    def test_tier_zero_and_explicit_clear_are_blank(self):
        self.assertFalse(any(render(Presentation.parse(snapshot(effective_tier=0))).buffer))
        clear = snapshot(event_id=None, icon_id=None, label="", effective_tier=0, remaining_ms=0)
        self.assertFalse(any(render(Presentation.parse(clear)).buffer))
        self.assertFalse(any(render(Presentation.parse(snapshot(remaining_ms=0))).buffer))

    def test_all_visible_tiers_have_distinct_static_treatments(self):
        frames = [bytes(render(Presentation.parse(snapshot(effective_tier=tier))).buffer)
                  for tier in range(1, 5)]
        self.assertEqual(len(set(frames)), 4)
        self.assertTrue(all(any(frame) for frame in frames))
        urgent = render(Presentation.parse(snapshot(effective_tier=4)))
        self.assertEqual(urgent.get(0, 0), 1)
        self.assertEqual(urgent.get(2, 2), 1)
        self.assertEqual(urgent.get(4, 4), 1)

    def test_icons_are_distinct_and_long_labels_are_bounded(self):
        frames = [bytes(render(Presentation.parse(snapshot(icon_id=icon))).buffer)
                  for icon in ("knock", "bell", "dog", "name", "smoke")]
        self.assertEqual(len(set(frames)), 5)
        self.assertEqual(len(render(Presentation.parse(snapshot(label="X" * 128))).buffer), 1024)

    def test_optional_nonurgent_labels_preserve_icon_and_urgent_text(self):
        for tier, icon_y in ((1, 42), (2, 5), (3, 14)):
            cue = Presentation.parse(snapshot(effective_tier=tier))
            labeled = render(cue)
            icon_only = render(cue, show_labels=False)
            self.assertNotEqual(labeled.buffer, icon_only.buffer)
            x0, x1 = (8, 25) if tier == 1 else (52, 77)
            bottom = icon_y + (17 if tier == 1 else 25)
            self.assertEqual(
                [labeled.get(x, y) for y in range(icon_y, bottom) for x in range(x0, x1)],
                [icon_only.get(x, y) for y in range(icon_y, bottom) for x in range(x0, x1)],
            )
            self.assertTrue(any(icon_only.buffer))
        urgent = Presentation.parse(snapshot(effective_tier=4))
        self.assertEqual(render(urgent).buffer, render(urgent, show_labels=False).buffer)

    def test_invalid_snapshot_rejected(self):
        for changes in (dict(effective_tier=5), dict(state_sequence=True),
                        dict(remaining_ms=-1), dict(icon_id="unknown"),
                        dict(icon_id=[]), dict(session_id=""), dict(event_id=None),
                        dict(schema_version=2), dict(label="")):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Presentation.parse(snapshot(**changes))
        with self.assertRaises(ValueError):
            Presentation.parse({})

    def test_monotonic_expiry_and_thirty_second_cap(self):
        now = [100.0]
        state = DisplayState(clock=lambda: now[0])
        state.connect("run-a")
        self.assertTrue(state.accept(snapshot(remaining_ms=90000)))
        now[0] = 129.99
        self.assertTrue(any(state.frame().buffer))
        now[0] = 130.0
        self.assertFalse(any(state.frame().buffer))

    def test_repolled_snapshot_never_extends_but_new_sequence_is_authoritative(self):
        now = [0.0]
        state = DisplayState(clock=lambda: now[0])
        state.connect("run-a")
        state.accept(snapshot(remaining_ms=3000))
        now[0] = 2.0
        self.assertFalse(state.accept(snapshot(remaining_ms=3000)))
        self.assertEqual(state.deadline, 3.0)
        now[0] = 3.0
        self.assertIsNone(state.tick())
        self.assertFalse(state.accept(snapshot(remaining_ms=3000)))
        self.assertIsNone(state.tick())
        # Backend resumed the interrupted cue with a newer sequence.
        self.assertTrue(state.accept(snapshot(state_sequence=2, remaining_ms=3000)))
        self.assertEqual(state.active.event_id, "event-a")

    def test_stale_sequence_cannot_replace_or_clear(self):
        state = DisplayState(clock=lambda: 0.0)
        state.connect("run-a")
        state.accept(snapshot(state_sequence=5))
        self.assertFalse(state.accept(snapshot(state_sequence=4, event_id="old")))
        self.assertFalse(state.accept(snapshot(state_sequence=5, effective_tier=0)))
        self.assertEqual(state.active.event_id, "event-a")

    def test_clear_and_disconnect_remove_pixels(self):
        state = DisplayState(clock=lambda: 0.0)
        self.assertFalse(state.accept(snapshot()))
        state.connect("run-a")
        state.accept(snapshot())
        state.accept(snapshot(state_sequence=2, effective_tier=0, remaining_ms=0))
        self.assertFalse(any(state.frame().buffer))
        state.accept(snapshot(state_sequence=3, event_id="new"))
        state.disconnect()
        self.assertFalse(any(state.frame().buffer))
        self.assertFalse(state.accept(snapshot(state_sequence=4)))

    def test_reconnect_keeps_sequence_and_new_session_accepts_restart(self):
        state = DisplayState(clock=lambda: 0.0)
        state.connect("run-a")
        state.accept(snapshot(state_sequence=20))
        state.disconnect()
        state.connect("run-a")
        self.assertFalse(state.accept(snapshot(state_sequence=1)))
        state.connect("run-b")
        self.assertFalse(state.accept(snapshot(state_sequence=99)))
        self.assertTrue(state.accept(snapshot(session_id="run-b", state_sequence=1)))
        self.assertEqual(state.sequence, 1)

    def test_cli_writes_offline_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "urgent.pbm"
            result = subprocess.run([sys.executable, "-m", "hardware.display", "--event", "smoke",
                                     "--tier", "4", "--output", str(output)],
                                    capture_output=True, text=True, check=True)
            self.assertIn("design preview", result.stdout)
            self.assertEqual(len(output.read_bytes()), 1034)


if __name__ == "__main__":
    unittest.main()
