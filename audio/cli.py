import argparse
import json
import queue
import sys
import time
from urllib.request import Request, urlopen
from audio.events import Detector, TARGETS, make_event, load_policy, runtime_model
from pathlib import Path

def publish(event, endpoint):
    payload = json.dumps(event, allow_nan=False)
    print(payload, flush=True)
    if endpoint:
        try:
            with urlopen(Request(endpoint, data=payload.encode(), headers={'Content-Type':'application/json'}), timeout=2) as response:
                response.read()
                return 'delivered'
        except Exception as exc:
            print(f'Event delivery failed: {exc}', file=sys.stderr)
            return 'failed'
    return 'stdout_only'

def main():
    parser = argparse.ArgumentParser(description='Local sound → event JSON')
    parser.add_argument('--model',choices=['yamnet','zipformer'],default=runtime_model())
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('devices')
    sub.add_parser('warmup')
    fake = sub.add_parser('fake')
    fake.add_argument('kind', choices=TARGETS)
    fake.add_argument('--endpoint', default='http://127.0.0.1:8765/events')
    for name in ('file', 'mic'):
        p = sub.add_parser(name)
        p.add_argument('--endpoint')
        p.add_argument('--debug', action='store_true')
        p.add_argument('--no-custom', action='store_true', help='ignore taught custom sounds')
        p.add_argument('--no-names', action='store_true', help='turn off name detection')
        p.add_argument('--observations', help='URL for per-window observations (default: next to --endpoint)')
        p.add_argument('--no-observations', action='store_true', help='do not stream per-window observations')
        p.add_argument('--observe-top', type=int, default=10, help='labels per observation (1..25)')
        p.add_argument('--decision-log',type=Path,default=Path(__file__).resolve().parent.parent/'.cache'/'recognition-decisions.jsonl')
        if name == 'file':
            p.add_argument('path')
            p.add_argument('--realtime', action='store_true')
        else:
            p.add_argument('--device', type=int)
            p.add_argument('--seconds', type=float, default=0, help='0 runs until Ctrl+C')
    args = parser.parse_args()
    if args.command == 'devices':
        import sounddevice as sd
        print(sd.query_devices())
        return
    if args.command == 'fake':
        publish(make_event(args.kind, 1, 'mock'), args.endpoint)
        return
    import numpy as np
    from audio.model import create_model, load_audio
    print(f'Loading {args.model}…', file=sys.stderr)
    custom = None
    if args.command in ('file', 'mic') and not args.no_custom and args.model == 'zipformer':
        try:
            # Same scores as the sherpa-onnx path, plus the embedding custom heads need.
            from audio.embeddings import ZipformerEmbedder
            model = ZipformerEmbedder()
            from audio.custom_sounds import CustomSoundDetector
            custom = CustomSoundDetector()
            print('Custom sounds: '+(', '.join(meta['label'] for meta, _ in custom.heads) or
                  'none yet (new ones load automatically)'), file=sys.stderr)
        except ImportError as exc:
            print(f'Custom sounds off ({exc.name} not installed; see requirements-audio.txt)', file=sys.stderr)
    if custom is None:
        model = create_model(args.model)
    model.predict(np.zeros(model.window_samples, dtype=np.float32))
    print(f'{args.model} ready', file=sys.stderr)
    if args.command == 'warmup':
        return
    detector = Detector(policy=load_policy(model_name=args.model))
    from audio.decision_log import DecisionLog
    decision_log=DecisionLog(args.decision_log)
    import atexit
    atexit.register(decision_log.close)
    decision_log.write(dict(kind='recognition_session',model=args.model,policy=detector.policy,
        window_samples=model.window_samples,hop_samples=model.hop_samples,sample_rate=16000))
    print(f'Decision log: {args.decision_log}',file=sys.stderr)
    observer=None
    observation_url=args.observations or (args.endpoint.rsplit('/events',1)[0]+'/observations'
                                         if args.endpoint and args.endpoint.endswith('/events') else None)
    if observation_url and not args.no_observations:
        from audio.observations import ObservationPublisher, MAX_TOP_K
        if not 1 <= args.observe_top <= MAX_TOP_K:
            parser.error(f'--observe-top must be 1..{MAX_TOP_K}')
        observer=ObservationPublisher(observation_url)
        atexit.register(observer.flush)
        print(f'Observations: {observation_url}',file=sys.stderr)

    names = None
    if not args.no_names:
        try:
            from audio.names import NameDetector
            names = NameDetector()
        except (ImportError, RuntimeError) as exc:
            print(f'Name detection off: {exc}', file=sys.stderr)
    name_events = []   # emitted since the last window, so observations can report them

    def hear_names(samples, source, clock=None, timestamp=None):
        """Feed new audio to the name spotter as soon as it arrives (0.2 s blocks from the mic)."""
        if names is None:
            return
        events = names.accept(samples, source, now=clock, timestamp_ms=timestamp)
        deliveries = [{'event_id':e['event_id'],'status':publish(e,args.endpoint)} for e in events]
        name_events.extend(events)
        if names.decisions:
            decision_log.write(dict(kind='name_detection',source=source,window_timestamp_ms=timestamp,
                decisions=names.decisions,deliveries=deliveries))

    def process(window, source, clock=None, timestamp=None):
        scores, elapsed = model.predict(window)
        if args.debug:
            print(json.dumps({'inference_ms':round(elapsed, 1), 'top5':sorted(scores.items(), key=lambda x:x[1], reverse=True)[:5]}), file=sys.stderr)
        events=detector.detect(scores, source, now=clock, timestamp_ms=timestamp)
        custom_decisions=[]
        if custom is not None:
            from audio.custom_sounds import rms
            events+=custom.detect(model.last_embedding, rms(window), source, now=clock, timestamp_ms=timestamp)
            custom_decisions=custom.decisions
        deliveries=[]
        for event in events:
            event['inference_ms'] = round(elapsed, 1)
            event['model'] = args.model
            deliveries.append({'event_id':event['event_id'],'status':publish(event,args.endpoint)})
        events_for_observation = events+name_events
        name_events.clear()
        if observer is not None:
            from audio.observations import build_observation
            from audio.custom_sounds import rms as window_rms
            observer.publish(build_observation(scores, source=source, model=args.model,
                timestamp_ms=timestamp, inference_ms=elapsed, window_rms=window_rms(window),
                rule_decisions=detector.decisions, custom_decisions=custom_decisions,
                custom_labels={m['id']:m['label'] for m,_ in custom.heads} if custom is not None else None,
                events=events_for_observation, top_k=args.observe_top,
                window_seconds=model.window_samples/16000, hop_seconds=model.hop_samples/16000))
        decision_log.write(dict(kind='recognition_window',source=source,model=args.model,
            window_timestamp_ms=timestamp,window_clock_seconds=clock,inference_ms=round(elapsed,1),
            top5=sorted(scores.items(),key=lambda x:x[1],reverse=True)[:5],
            decisions=detector.decisions+custom_decisions,deliveries=deliveries))

    if args.command == 'file':
        data = load_audio(args.path)
        base = int(time.time()*1000)
        start = time.monotonic()
        for offset in range(0, len(data), model.hop_samples):
            window = data[offset:offset+model.window_samples]
            if len(window) < model.window_samples:
                window = np.pad(window, (0, model.window_samples-len(window)))
            position = offset/16000
            if args.realtime:
                time.sleep(max(0, start+position+min(model.window_samples,len(data)-offset)/16000-time.monotonic()))
            end = position+min(model.window_samples,len(data)-offset)/16000
            fresh = data[0 if offset == 0 else offset+model.window_samples-model.hop_samples:offset+model.window_samples]
            if len(fresh):
                hear_names(fresh, 'replay', end, base+int(end*1000))
            process(window, 'replay', position, base+int(end*1000))
        hear_names(np.zeros(8000, dtype=np.float32), 'replay', len(data)/16000+0.5, base+int(len(data)/16+500))
        return
    import sounddevice as sd
    # 0.2 s blocks so the name spotter hears speech quickly; sound windows still run every hop.
    block_samples = 3200 if model.hop_samples % 3200 == 0 else model.hop_samples
    pending = queue.Queue(maxsize=max(4, 4*model.hop_samples//block_samples))
    def callback(indata, frames, timing, status):
        if status:
            print(f'Audio capture: {status}', file=sys.stderr)
        item = (indata[:, 0].copy(), time.monotonic(), int(time.time()*1000))
        try:
            pending.put_nowait(item)
        except queue.Full:
            pending.get_nowait()
            pending.put_nowait(item)
            print('Dropped audio block: processing is behind', file=sys.stderr)
    buffer = np.empty(0, dtype=np.float32)
    last_capture = None
    start = time.monotonic()
    with sd.InputStream(device=args.device, channels=1, samplerate=16000,
                        blocksize=block_samples, dtype='float32', callback=callback):
        print('Microphone active; Ctrl+C stops. Raw audio is not saved.', file=sys.stderr)
        while not args.seconds or time.monotonic()-start < args.seconds:
            block, captured, wall = pending.get(timeout=3)
            if last_capture is not None and captured-last_capture > 1.5*block_samples/16000:
                buffer = np.empty(0, dtype=np.float32)
                if names is not None:
                    names.reset()
            last_capture = captured
            hear_names(block, 'microphone', captured, wall)
            buffer = np.concatenate((buffer, block))
            if len(buffer) >= model.window_samples:
                process(buffer[-model.window_samples:], 'microphone', captured, wall)
                buffer = buffer[-(model.window_samples-model.hop_samples):]

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
