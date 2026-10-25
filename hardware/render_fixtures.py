"""Regenerate hardware/render-fixtures.json: python3 -m hardware.render_fixtures

The browser preview (frontend/src/lib/oled.ts) must reproduce these frames byte for byte.
"""
import json
from pathlib import Path
from hardware.display import DIRECTIONS, ICON_IDS, Presentation, render

PATH = Path(__file__).with_name('render-fixtures.json')
LABELS = {'knock': 'Door knock', 'bell': 'Bell / chime', 'dog': 'Dog barking', 'name': 'Your name',
          'smoke': 'Smoke alarm', 'siren': 'Siren', 'clock': 'Alarm clock', 'chat': 'Conversation', 'check': 'Done',
          'person': 'Baby cry', 'paw': 'Cat', 'music': 'Saxophone', 'cloud': 'Thunder', 'drop': 'Water tap',
          'car': 'Vehicle horn', 'house': 'Microwave oven', 'gear': 'Power tool', 'bang': 'Gunshot',
          'wave': 'Sound'}

LABELS.update({cue['icon_id']: cue['label'] for cue in json.loads(
    (Path(__file__).parent.parent / 'audio/cue-catalog.json').read_text())['cues']})


def cases():
    for icon in sorted(ICON_IDS):
        for tier in range(5):
            for labels in (True, False):
                yield dict(icon_id=icon, label=LABELS[icon], effective_tier=tier, remaining_ms=3000, show_labels=labels)
    yield dict(icon_id='knock', label='A very long label that needs wrapping onto two lines', effective_tier=2,
               remaining_ms=3000, show_labels=True)
    for label in ('门铃 🔔', '🚨' * 24, 'Straße alarm', '  Alarm\t clock  '):
        for direction in (None, 'left', 'right', 'behind'):
            yield dict(icon_id='bell', label=label, effective_tier=4, remaining_ms=3000,
                       show_labels=True, direction=direction)
    for direction in DIRECTIONS:
        for tier in range(1, 5):
            yield dict(icon_id='smoke', label='Smoke alarm', effective_tier=tier, remaining_ms=3000,
                       show_labels=True, direction=direction)
        yield dict(icon_id='knock', label='A very long label that needs wrapping onto two lines', effective_tier=2,
                   remaining_ms=3000, show_labels=True, direction=direction)

    for index in range(16):
        bearing = index * 22.5
        if bearing > 180:
            bearing -= 360
        for labels in (False, True):
            yield dict(icon_id='smoke', label='Fire / smoke alarm', effective_tier=4,
                       remaining_ms=3000, show_labels=labels, direction='front', bearing_degrees=bearing)


def frames():
    out = []
    for case in cases():
        cue = Presentation.parse(dict(schema_version=1, session_id='fixture', state_sequence=1,
                                      event_id='fixture' if case['effective_tier'] else None,
                                      label=case['label'] if case['effective_tier'] else '',
                                      icon_id=case['icon_id'] if case['effective_tier'] else None,
                                      effective_tier=case['effective_tier'], remaining_ms=case['remaining_ms'],
                                      direction=case.get('direction'), bearing_degrees=case.get('bearing_degrees')))
        out.append(dict(case, frame=render(cue, case['show_labels']).buffer.hex()))
    return out


if __name__ == '__main__':
    PATH.write_text(json.dumps(frames()) + '\n')
    print(f'Wrote {PATH}')
