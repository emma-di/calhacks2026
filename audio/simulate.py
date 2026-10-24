"""Recorded-audio scenarios exercise the real model, detector and alert state offline."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from audio.benchmark import windows, DATA, REPORTS
from audio.events import Detector, load_policy, runtime_model
from audio.model import create_model, load_audio
from audio.server import AlertState

def build_scenarios(manifest):
    # Fixed sources from tuning split; demonstration fixtures are not evaluation claims.
    def clip(kind):
        row=next(r for r in manifest['clips'] if r['split']=='tune' and kind in r['expected'])
        signal=load_audio(DATA/row['path'])[:80000]
        return np.pad(signal,(0,max(0,80000-len(signal)))),row['id']
    sounds={kind:clip(kind) for kind in ('dog_bark','knock','siren','alarm_clock','smoke_alarm','bicycle_bell')}
    silence=np.zeros(96000,dtype=np.float32)
    signals=[silence];regions=[];position=6
    for kind,(signal,source_id) in sounds.items():
        signals.extend((signal,silence))
        regions.append(dict(type='bell' if kind=='bicycle_bell' else kind,start=position,end=position+5,source_id=source_id))
        position+=11
    alarm=sounds['smoke_alarm'][0];dog=sounds['dog_bark'][0]
    overlap=.65*alarm+.35*dog
    knock=np.tile(sounds['knock'][0],4)
    return [
        dict(name='separated-events',signal=np.concatenate(signals),regions=regions),
        dict(name='overlapping-dog-and-smoke',signal=np.concatenate((silence,overlap,silence)),
             regions=[dict(type=kind,start=6,end=11,source_id=sounds[kind][1]) for kind in ('smoke_alarm','dog_bark')]),
        dict(name='repeated-knocks',signal=np.concatenate((silence,knock,silence)),
             regions=[dict(type='knock',start=6,end=26,source_id=sounds['knock'][1])]),
        dict(name='silence',signal=np.zeros(160000,dtype=np.float32),regions=[]),
    ]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',choices=['yamnet','zipformer'],default=runtime_model())
    args=p.parse_args()
    model=create_model(args.model)
    manifest=json.loads((DATA/'manifest.json').read_text())
    outputs=[]
    for scenario in build_scenarios(manifest):
        detector=Detector(policy=load_policy(model_name=args.model));state=AlertState();events=[];decisions=[]
        for position,window in windows(scenario['signal'],model.window_samples,model.hop_samples):
            completed=position+model.window_samples/16000
            scores,elapsed=model.predict(window)
            detected=detector.detect(scores,'simulation',now=completed,timestamp_ms=int(completed*1000))
            decisions.extend(dict(window_seconds=completed,**decision) for decision in detector.decisions
                             if decision['raw_score']>=decision['threshold'])
            for event in detected:
                event['scenario_seconds']=round(completed,3)
                event['model']=args.model
                state.add(event,now=completed)
                events.append(dict(event=event,active_type=state.snapshot(now=completed)['active']['type']))
        hits=[dict(**region,detected=any(e['event']['type']==region['type'] and
                region['start']<=e['event']['scenario_seconds']<=region['end']+2 for e in events))
              for region in scenario['regions']]
        outputs.append(dict(name=scenario['name'],duration_seconds=len(scenario['signal'])/16000,
            expected_regions=hits,events=events,recognition_decisions=decisions,
            alert_decisions=list(state.decisions),active_after_timeout=state.snapshot(now=10000)['active']))
        print(scenario['name'],json.dumps({'hits':hits,'event_types':[x['event']['type'] for x in events]}),flush=True)
    REPORTS.mkdir(exist_ok=True)
    (REPORTS/f'{args.model}-scenarios.json').write_text(json.dumps(dict(model=args.model,scenarios=outputs),indent=2)+'\n')

if __name__=='__main__':
    main()
