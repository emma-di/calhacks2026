"""Curated symbols must stay distinct, complete, and renderable without Pi hardware."""
import json
from pathlib import Path
import unittest

from hardware.cue_icons import build_cue_icons
from hardware.icons import Canvas, ICONS
from hardware.display import Presentation, render

ROOT = Path(__file__).resolve().parents[1]


class CuratedCueIconsTest(unittest.TestCase):
    def test_all_fifty_approved_cues_have_distinct_binary_symbols(self):
        cues = json.loads((ROOT / 'audio/cue-catalog.json').read_text())['cues']
        baked = json.loads((ROOT / 'hardware/oled-assets.json').read_text())['bitmaps']
        generated = build_cue_icons(Canvas, ICONS)
        self.assertEqual(len(cues), 50)
        self.assertEqual(set(generated), {cue['icon_id'] for cue in cues})
        shapes = set()
        for key, canvas in generated.items():
            rows = canvas.rows()
            self.assertEqual(rows, baked[key], key)
            self.assertEqual(len(rows), 32, key)
            self.assertTrue(all(len(row) == 32 and set(row) <= {'0', '1'} for row in rows), key)
            self.assertGreater(sum(row.count('1') for row in rows), 60, key)
            shapes.add(tuple(rows))
        self.assertEqual(len(shapes), 50, 'Every curated cue needs its own visual identity')

    def test_original_nineteen_remain_unchanged_and_all_cues_render(self):
        baked = json.loads((ROOT / 'hardware/oled-assets.json').read_text())['bitmaps']
        self.assertEqual(len(ICONS), 19)
        for key, make in ICONS.items():
            self.assertEqual(baked[key], make().rows(), key)
        for cue in json.loads((ROOT / 'audio/cue-catalog.json').read_text())['cues']:
            frames = []
            for bearing in (None, -157.5, -90, 0, 67.5, 180):
                presentation = Presentation.parse(dict(
                    schema_version=1, session_id='curated-test', state_sequence=1,
                    event_id=cue['id'], icon_id=cue['icon_id'], label=cue['label'],
                    effective_tier=2, remaining_ms=3000,
                    direction='front' if bearing is not None else None,
                    bearing_degrees=bearing))
                bitmap = render(presentation, False)
                self.assertEqual(len(bitmap.buffer), 1024)
                self.assertEqual(len(bitmap.ssd1306_pages()), 1024)
                frames.append(bytes(bitmap.buffer))
            self.assertEqual(len(set(frames)), 6, cue['id'])


if __name__ == '__main__':
    unittest.main()
