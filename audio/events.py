"""Hardware-independent event contract and provisional detection policy."""
import math
import time
import uuid
import json
from pathlib import Path

# Exact YAMNet class names. Thresholds are starting points, not calibrated probabilities.
TARGETS = {
    'knock': ('Knock', 'Door knock', 2, 0.30),
    'bicycle_bell': ('Bicycle bell', 'Bicycle bell', 2, 0.30),
    'dog_bark': ('Bark', 'Dog barking', 1, 0.30),
    'siren': ('Siren', 'Siren', 3, 0.40),
    'smoke_alarm': ('Smoke detector, smoke alarm', 'Smoke alarm', 4, 0.40),
    'alarm_clock': ('Alarm clock', 'Alarm clock', 2, 0.40),
    'bell': ('Bell', 'Bell / chime', 2, 0.30),
}
# Every type the receiver accepts. name_called comes from the planned speech worker, not the classifier.
EVENT_TYPES = {kind:(label, tier) for kind,(_, label, tier, _) in TARGETS.items()}
EVENT_TYPES['name_called'] = ('Your name', 3)

def runtime_model():
    path=Path(__file__).with_name('runtime.json')
    return json.loads(path.read_text())['model'] if path.exists() else 'yamnet'

def load_policy(path=None, model_name=None):
    model_name=runtime_model() if model_name is None else model_name
    path = Path(path) if path else Path(__file__).with_name(f'policy-{model_name}.json')
    if path.exists():
        return json.loads(path.read_text())
    return dict(version=1, cooldown_seconds=5, rules={
        kind:dict(labels={entry[0]:1},threshold=entry[3],status='baseline')
        for kind,entry in TARGETS.items()})

def evaluate_rule(scores, rule, now=None, state=None):
    values = [float(scores.get(label, 0))*weight for label,weight in rule['labels'].items()]
    raw=max((value for value in values if math.isfinite(value) and 0<=value<=1), default=0)
    decision={'raw_score':raw,'threshold':rule['threshold'],'reason':'eligible'}
    active={label:float(scores.get(label,0)) for label,threshold in rule.get('suppressors',{}).items()
            if float(scores.get(label,0))>=threshold}
    if active:
        if state is not None and now is not None:
            state['blocked_until']=now+rule.get('suppressor_hold_seconds',0)
            state['last_context']={'labels':active,'seen_at_seconds':now}
        decision.update(reason='suppressed_current_context',context_labels=active)
        return 0,decision
    if state is not None and now is not None and now<state.get('blocked_until',-math.inf):
        decision.update(reason='suppressed_recent_context',recent_context=state.get('last_context'),
                        hold_remaining_seconds=round(state['blocked_until']-now,3))
        return 0,decision
    return raw,decision

def event_score(scores, rule, now=None, state=None):
    # Tuning evaluates label templates before assigning a threshold.
    return evaluate_rule(scores,dict(rule,threshold=rule.get('threshold',0)),now,state)[0]

def make_event(kind, confidence, source, timestamp_ms=None):
    _, label, tier, _ = TARGETS[kind]
    return dict(schema_version=1, event_id=str(uuid.uuid4()), type=kind,
                label=label, confidence=float(confidence), source=source,
                priority_tier=tier, timestamp_ms=timestamp_ms if timestamp_ms is not None else int(time.time()*1000),
                direction_degrees=None, direction_confidence=None,
                distance_meters=None, proximity='unknown')

def validate_event(event):
    if not isinstance(event, dict) or event.get('type') not in EVENT_TYPES:
        raise ValueError('Unknown event type')
    if event.get('schema_version') != 1:
        raise ValueError('Expected schema_version 1')
    for key in ('event_id', 'label', 'source'):
        if not isinstance(event.get(key), str) or not 0 < len(event[key]) <= 120:
            raise ValueError(f'Invalid {key}')
    score = event.get('confidence')
    # Nullable for workers without a calibrated score (NAME-04); the UI never formats a missing score.
    if score is not None and (type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1):
        raise ValueError('confidence must be null or finite within 0..1')
    if type(event.get('priority_tier')) is not int or not 0 <= event['priority_tier'] <= 4:
        raise ValueError('priority_tier must be 0..4')
    if type(event.get('timestamp_ms')) is not int or event['timestamp_ms'] < 0:
        raise ValueError('timestamp_ms must be a nonnegative integer')
    # Direction is deliberately unsupported until a localization adapter is validated.
    if any(event.get(k) is not None for k in ('direction_degrees', 'direction_confidence', 'distance_meters')):
        raise ValueError('Spatial estimates are not supported yet')
    return event

class Detector:
    def __init__(self, cooldown=None, policy=None):
        self.policy = load_policy() if policy is None else policy
        self.cooldown = self.policy.get('cooldown_seconds',5) if cooldown is None else cooldown
        self.last = {}
        self.rule_states = {kind:{} for kind in self.policy['rules']}
        self.decisions=[]

    def detect(self, scores, source, now=None, timestamp_ms=None):
        now = time.monotonic() if now is None else now
        events = []
        self.decisions=[]
        for kind, rule in self.policy['rules'].items():
            score,decision=evaluate_rule(scores,rule,now,self.rule_states[kind])
            decision.update(type=kind,effective_score=score)
            if not rule.get('enabled',True):
                decision['reason']='disabled'
                self.decisions.append(decision)
                continue
            if decision['reason']!='eligible':
                self.decisions.append(decision)
                continue
            if score<rule['threshold']:
                decision['reason']='below_threshold'
            elif now-self.last.get(kind,-math.inf)<self.cooldown:
                decision.update(reason='cooldown',cooldown_remaining_seconds=round(self.cooldown-(now-self.last[kind]),3))
            else:
                event=make_event(kind, score, source, timestamp_ms)
                events.append(event)
                self.last[kind] = now
                decision.update(reason='emitted',event_id=event['event_id'])
            self.decisions.append(decision)
        return events
