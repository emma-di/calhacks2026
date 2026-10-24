"""Offline evaluation on fixed source splits; tuning never uses held-out clips."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from audio.model import create_model, load_audio, ROOT

DATA = ROOT/'samples'/'benchmark'
CACHE = ROOT/'.cache'/'benchmark'
REPORTS = ROOT/'reports'
LABELS = ['Knock','Bicycle bell','Bark','Bow-wow','Yip','Dog','Siren','Civil defense siren',
          'Smoke detector, smoke alarm','Fire alarm','Alarm','Alarm clock','Buzzer']
BASE_LABELS=list(LABELS)
LABELS += ['Bell','Ding','Chime']
DEFAULTS = {
    'knock': {'labels':{'Knock':1}, 'threshold':.30},
    'bicycle_bell': {'labels':{'Bicycle bell':1}, 'threshold':.30},
    'dog_bark': {'labels':{'Bark':1}, 'threshold':.30},
    'siren': {'labels':{'Siren':1}, 'threshold':.40},
    'smoke_alarm': {'labels':{'Smoke detector, smoke alarm':1}, 'threshold':.40},
    'alarm_clock': {'labels':{'Alarm clock':1}, 'threshold':.40},
    'bell': {'labels':{'Bell':1,'Ding':1,'Chime':1},'threshold':.30},
}
CANDIDATES = {
    'knock':[{'Knock':1}],
    'bicycle_bell':[{'Bicycle bell':1}],
    'dog_bark':[{'Bark':1}, {'Bark':1,'Bow-wow':1,'Yip':1},
                {'Bark':1,'Bow-wow':1,'Yip':1,'Dog':.5}],
    'siren':[{'Siren':1}, {'Siren':1,'Civil defense siren':1}],
    'smoke_alarm':[{'Smoke detector, smoke alarm':1}],
    'alarm_clock':[{'Alarm clock':1}],
    'bell':[{'Bell':1},{'Bell':1,'Ding':1,'Chime':1}],
}

def windows(data, size=15600, hop=7680):
    for offset in range(0, len(data), hop):
        window = data[offset:offset+size]
        if len(window)<size:
            window = np.pad(window,(0,size-len(window)))
        yield offset/16000, window

def transform(data, variant, seed):
    if variant == 'clean':
        return data
    if variant == 'quiet':
        return data * .15  # -16.5 dB attenuation; no normalization afterwards
    rng = np.random.default_rng(seed)
    if variant == 'noise10':
        # Controlled white noise at +10 dB signal-to-noise ratio, not room noise.
        rms = np.sqrt(np.mean(data**2))
        noise = rng.normal(0,1,len(data)).astype(np.float32)
        noise *= rms / (np.sqrt(np.mean(noise**2))+1e-9) / np.sqrt(10)
        mixed = data+noise
    elif variant == 'echo':
        mixed = data.copy()
        for delay, gain in [(640,.40),(1920,.25),(3520,.12)]:
            if len(data)>delay:
                mixed[delay:] += gain*data[:-delay]
    else:
        raise ValueError(variant)
    return mixed / max(1,float(np.max(np.abs(mixed))))

def extract(manifest, variants, model_name):
    CACHE.mkdir(parents=True, exist_ok=True)
    model = create_model(model_name)
    model.predict(np.zeros(model.window_samples,dtype=np.float32))
    records=[]
    for n,row in enumerate(manifest['clips'],1):
        data = load_audio(DATA/row['path'])
        for variant in variants:
            signature='yamnet1-w15600-h7680-v1' if model_name=='yamnet' else model.model_id+str(model.window_samples)+str(model.hop_samples)+'v2-bell'
            key = hashlib.sha256((row['sha256']+variant+signature).encode()).hexdigest()
            path = CACHE/(key+'.npz')
            if path.exists():
                saved = np.load(path)
                values, times = saved['values'], saved['times']
                if values.shape[1]!=len(LABELS):
                    path=path.with_name(path.stem+'-bell.npz')
                    if path.exists():
                        saved=np.load(path);values,times=saved['values'],saved['times']
            if not path.exists():
                signal=transform(data,variant,int(row['sha256'][:8],16))
                values,times=[],[]
                for _,window in windows(signal,model.window_samples,model.hop_samples):
                    scores,elapsed=model.predict(window)
                    values.append([scores[label] for label in LABELS]);times.append(elapsed)
                values,times=np.asarray(values),np.asarray(times)
                np.savez_compressed(path,values=values,times=times)
            expected=list(row['expected'])
            if 'bicycle_bell' in expected or row['category']=='church_bells':
                expected.append('bell')
            current=dict(row,expected=expected)
            records.append(dict(**current,variant=variant,duration=len(data)/16000,
                                hop_seconds=model.hop_samples/16000,
                                scores=dict(zip(LABELS,values.max(axis=0).tolist())),
                                windows=values.tolist(),inference_ms=times.tolist()))
        if n%25==0 or n==len(manifest['clips']):
            print(f'Scored {n}/{len(manifest["clips"])} source recordings × {len(variants)} conditions',flush=True)
    return records

def score(row, rule):
    if rule.get('suppressors'):
        from audio.events import event_score
        state={}
        return max(event_score(dict(zip(LABELS,window)),rule,now=index*row['hop_seconds'],state=state)
                   for index,window in enumerate(row['windows']))
    return max(row['scores'].get(label,0)*weight for label,weight in rule['labels'].items())

def metrics(rows, kind, rule):
    tp=fp=fn=tn=0
    misses=[];false=[]
    for row in rows:
        actual=kind in row['expected']; predicted=rule.get('enabled',True) and score(row,rule)>=rule['threshold']
        tp+=int(actual and predicted);fp+=int(not actual and predicted)
        fn+=int(actual and not predicted);tn+=int(not actual and not predicted)
        if actual and not predicted: misses.append(row['id'])
        if not actual and predicted: false.append(row['id'])
    precision=tp/(tp+fp) if tp+fp else None
    recall=tp/(tp+fn) if tp+fn else None
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,precision=precision,recall=recall,
                false_positive_rate=fp/(fp+tn) if fp+tn else None,
                missed_ids=misses,false_positive_ids=false)

def tune(rows, model_name, previous=None, tune_only=None):
    policy={}
    for kind,baseline in DEFAULTS.items():
        if tune_only is not None and kind not in tune_only and previous is not None:
            policy[kind]=previous['rules'][kind]
            continue
        positives=sum(kind in r['expected'] for r in rows)
        if not positives:
            policy[kind]=dict(**baseline,status='unvalidated_no_tuning_positives')
            continue
        best=None
        # Every row is one source+condition. Restrict false positives on tuning set to <=1%.
        for weights in CANDIDATES[kind]:
            for hold in ([None,0,2,4] if kind=='bell' else [None]):
                template={'labels':weights}
                if hold is not None:
                    template['suppressors']={label:policy[target]['threshold'] for target,label in
                        [('alarm_clock','Alarm clock'),('smoke_alarm','Smoke detector, smoke alarm'),('siren','Siren')]}
                    template['suppressor_hold_seconds']=hold
                cached=[dict(row,scores={'_score':score(row,template)}) for row in rows]
                for threshold in np.arange(.05, .951, .025):
                    rule=dict(template,threshold=round(float(threshold),3))
                    m=metrics(cached,kind,{'labels':{'_score':1},'threshold':rule['threshold']})
                    if m['false_positive_rate']>.01:
                        continue
                    rank=(m['recall'], -(m['fp']),rule['threshold'])
                    if best is None or rank>best[0]:
                        best=(rank,rule)
        chosen=best[1] if best else baseline
        positive_sources=len({row['source_group'] for row in rows if kind in row['expected']})
        status='tuned_on_source_split' if positive_sources>=5 else 'provisional_small_sample'
        policy[kind]=dict(**chosen,status=status)
        if metrics(rows,kind,chosen)['tp']==0:
            policy[kind].update(enabled=False,status='disabled_no_tuning_hits')
        if kind=='bicycle_bell':
            policy[kind].update(enabled=False,status='disabled_source_specificity_unvalidated')
    return dict(version=1,model=model_name,cooldown_seconds=5,
                tuning='ESC-50 folds 1–3 and designated supplemental authors only; false-positive rate <=1% on tuning cases',
                rules=policy)

def percent(value):
    return 'n/a' if value is None else f'{100*value:.1f}%'

def report(records, policy, manifest, model_name, previous=None):
    result={'model':model_name,'source_recordings':len(manifest['clips']),
            'cases':len(records),'variants':sorted({r['variant'] for r in records}),
            'policy':policy,'metrics':{},'missing_sources':manifest['missing_sources'],
            'download_errors':manifest['download_errors']}
    if previous is not None:
        result['previous_policy_metrics']={variant:{kind:metrics(
            [row for row in records if row['split']=='test' and row['variant']==variant],kind,rule)
            for kind,rule in previous['rules'].items()} for variant in sorted({row['variant'] for row in records})}
    lines=['# Offline sound benchmark — '+model_name,'',
           'Tuning uses source folds 1–3; held-out evaluation uses folds 4–5. Supplemental authors are assigned tune/test before inference. Related variants stay in the same split.',
           'Evaluation recordings are held out from fitting thresholds, but results have been inspected during development; this is not a blind certification test.',
           'Precision/recall are per recording (any qualifying window); these are not temporal localization or field reliability scores.',
           'Public sources may overlap pretrained-model training data. Negative sound labels are not exhaustively multi-label annotated.','',
           f'Source recordings: {len(manifest["clips"])}. Cases including transformations: {len(records)}.','',
           '| Condition | Event | Held-out hits / positives | Precision | False alarms / negatives | Baseline recall → tuned recall |',
           '| --- | --- | --- | --- | --- | --- |']
    for variant in sorted({r['variant'] for r in records}):
        rows=[r for r in records if r['split']=='test' and r['variant']==variant]
        result['metrics'][variant]={}
        for kind,rule in policy['rules'].items():
            m=metrics(rows,kind,rule);before=metrics(rows,kind,DEFAULTS[kind])
            result['metrics'][variant][kind]={'baseline':before,'tuned':m}
            lines.append(f'| {variant} | {kind} | {m["tp"]}/{m["tp"]+m["fn"]} | {percent(m["precision"])} | {m["fp"]}/{m["fp"]+m["tn"]} | {percent(before["recall"])} → {percent(m["recall"])} |')
    latencies=[t for r in records for t in r['inference_ms']]
    result['inference_ms']={'median':float(np.median(latencies)),'p95':float(np.percentile(latencies,95))}
    lines+=['','## Applied policy','', '```json',json.dumps(policy,indent=2),'```','',
            '## Coverage gaps','',*['- '+x for x in manifest['missing_sources']],
            '- No final hardware microphone, speech/name matching, or real-room evaluation in this benchmark.',
            '- Quiet means amplitude ×0.15; noise10 means deterministic white noise at +10 dB SNR; echo uses synthetic delayed reflections.',
            '- These variants are robustness probes, not independent recordings or a substitute for acoustic testing.',
            '- A false alert on a sparsely labeled clip needs listening review: a second sound may genuinely be present.','',
            f'Inference median {result["inference_ms"]["median"]:.2f} ms; p95 {result["inference_ms"]["p95"]:.2f} ms. Excludes collection and display delay.','']
    REPORTS.mkdir(exist_ok=True)
    (REPORTS/f'{model_name}.json').write_text(json.dumps(result,indent=2)+'\n')
    (REPORTS/f'{model_name}.md').write_text('\n'.join(lines))
    # Exclude per-window values from the compact review artifact; cache retains exact windows.
    compact=[{k:v for k,v in row.items() if k not in ('windows','inference_ms')} for row in records]
    (REPORTS/f'{model_name}-cases.json').write_text(json.dumps(compact,indent=2)+'\n')
    print('\n'.join(lines[:17]),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',choices=['yamnet','zipformer'],default='yamnet')
    p.add_argument('--baseline-policy',type=Path)
    p.add_argument('--tune-only',nargs='+',choices=list(DEFAULTS))
    p.add_argument('--variants',nargs='+',default=['clean','quiet','noise10','echo'],choices=['clean','quiet','noise10','echo'])
    args=p.parse_args()
    manifest=json.loads((DATA/'manifest.json').read_text())
    records=extract(manifest,args.variants,args.model)
    tuning=[r for r in records if r['split']=='tune']
    previous=json.loads(args.baseline_policy.read_text()) if args.baseline_policy else None
    if args.tune_only and previous is None:
        p.error('--tune-only requires --baseline-policy')
    policy=tune(tuning,args.model,previous,args.tune_only)
    (ROOT/'audio'/f'policy-{args.model}.json').write_text(json.dumps(policy,indent=2)+'\n')
    report(records,policy,manifest,args.model,previous)

if __name__=='__main__':
    main()
