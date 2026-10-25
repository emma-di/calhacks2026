"""Seeded cross-language stress test; no hardware/capture or running receiver required.

Run: .venv/bin/python scripts/verify_alert_parity.py --steps 10000 --seed 20261024
"""
import argparse
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio.alerts import AlertEngine, POLICY
from audio.events import EVENT_TYPES
from hardware.display import Presentation, render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=20261024)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    engine = AlertEngine()
    actions, expected = [], []
    kinds = ['knock', 'bell', 'dog_bark', 'name_called', 'smoke_alarm', 'siren', 'alarm_clock', 'custom']
    taught = ['front-doorbell', 'kettle', 'microwave']   # separate custom sounds share type 'custom'
    at, ids = 0, []
    for index in range(args.steps):
        at += rng.randrange(1, 2500)
        choice = rng.random()
        action = dict(at=at)
        if choice < .65:
            kind = rng.choice(kinds)
            label, tier = EVENT_TYPES[kind]
            event_id = rng.choice(ids) if ids and rng.random() < .05 else f'soak-{index}'
            ids = (ids + [event_id])[-256:]
            degrees = rng.choice([None, -90, 0, 90, 180])
            event = dict(schema_version=1, event_id=event_id, type=kind, label=label,
                         source='simulation', priority_tier=tier, confidence=None, timestamp_ms=at,
                         direction_degrees=degrees, direction_confidence=None if degrees is None else rng.choice([.2, .6, 1]),
                         distance_meters=None)
            if kind == 'custom':
                sound = rng.choice(taught)
                event.update(custom_sound_id=sound, label=sound, priority_tier=rng.choice([1, 2, 3]))
            action['event'] = event
            engine.add(event, at)
        elif choice < .79:
            action['controls'] = dict(focus_mode=rng.choice(['everyday', 'work', 'dnd']), paused=rng.random() < .2)
            engine.set_controls(at, **action['controls'])
        elif choice < .91:
            action['dismiss'] = engine.active['event']['event_id'] if engine.active and rng.random() < .8 else 'stale-id'
            engine.dismiss(at, action['dismiss'])
        else:
            engine.tick(at)
        actions.append(action)
        s = engine.snapshot(at)
        assert len(s['queue']) <= POLICY['queue_limit'], (index, 'unbounded queue')
        assert len(s['events']) <= 50 and len(s['decisions']) <= 50, (index, 'unbounded history')
        assert s['remaining_ms'] >= 0
        if s['paused']:
            assert s['active'] is None and s['confirm'] is None and not s['queue'], (index, 'pause leaked a cue')
        frame = render(Presentation.parse(engine.presentation(at)), show_labels=False)
        assert len(frame.buffer) == 1024
        expected.append(dict(active=[s['active']['event_id'], s['active']['priority_tier']] if s['active'] else None,
                             remaining=s['remaining_ms'], sequence=s['state_sequence'], direction=s['direction'],
                             confirm=s['confirm'], queue=s['queue'], paused=s['paused'], focus=s['focus_mode'],
                             last=[s['decisions'][-1]['event_id'], s['decisions'][-1]['reason']] if s['decisions'] else None))
    result = subprocess.run(['node', '--import', 'tsx', 'scripts/alert-parity.ts'], cwd=ROOT / 'frontend',
                            input=json.dumps(actions), capture_output=True, text=True, check=True)
    actual = json.loads(result.stdout)
    assert len(actual) == len(expected)
    for index, (left, right) in enumerate(zip(expected, actual)):
        assert left == right, json.dumps(dict(step=index, action=actions[index], recent_actions=actions[max(0,index-8):index], python=left, browser=right), indent=2)
    print(json.dumps(dict(status='passed', seed=args.seed, actions=args.steps,
                          simulated_hours=round(at / 3600000, 2), cross_language_snapshots=len(actual),
                          render_checks=args.steps, hardware_used=False), indent=2))


if __name__ == '__main__':
    main()
