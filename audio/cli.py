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
        p.add_argument('--no-questions', action='store_true', help='do not transcribe questions after your name')
        p.add_argument('--observations', help='URL for per-window observations (default: next to --endpoint)')
        p.add_argument('--no-observations', action='store_true', help='do not stream per-window observations')
        p.add_argument('--observe-top', type=int, default=10, help='labels per observation (1..25)')
        p.add_argument('--decision-log',type=Path,default=Path(__file__).resolve().parent.parent/'.cache'/'recognition-decisions.jsonl')
        if name == 'file':
            p.add_argument('path')
            p.add_argument('--realtime', action='store_true')
        else:
            p.add_argument('--device', type=int)
            p.add_argument('--pi', help='Primary stereo input over SSH, e.g. pi@glasses-pi.local; no Mac mic opened')
            p.add_argument('--pi-device', default='hw:CARD=AwareINMP441,DEV=0')
            p.add_argument('--levels-port', type=int, default=8768)
            p.add_argument('--seconds', type=float, default=0, help='0 runs until Ctrl+C')
    args = parser.parse_args()
    if args.command == 'mic' and args.pi and args.device is not None:
        parser.error('Choose --pi OR --device; Mac fallback must be selected explicitly')
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
        audio_input=('pi_stereo' if args.command == 'mic' and args.pi else args.command),
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
    questions = None
    if names is not None and not args.no_questions:
        try:
            from audio.questions import QuestionCatcher
            questions = QuestionCatcher(
                on_event=lambda event: publish(event, args.endpoint), profile=lambda: names.profile,
                paraphrase_url=args.endpoint.rsplit('/', 1)[0] + '/questions/paraphrase' if args.endpoint else None,
                on_decision=lambda decision: decision_log.write(dict(kind='question', **decision)))
            print('Questions after your name: transcribed on this laptop, audio not saved', file=sys.stderr)
        except (ImportError, RuntimeError) as exc:
            print(f'Question capture off: {exc}', file=sys.stderr)
    from audio.custom_rules import CustomRules
    catalog = CustomRules()
    name_decisions = []
    snap_latched = False
    from audio.runtime_controls import RecognitionControls
    controls = RecognitionControls(args.endpoint)

    def refresh_controls():
        suppression = controls.refresh()
        for worker in (detector, names, custom, catalog):
            if worker is not None:
                worker.repeat_suppression = suppression

    def hear_names(samples, source, clock=None, timestamp=None, spatial_frames=None):
        """Feed new audio to the name spotter as soon as it arrives (0.2 s blocks from the mic)."""
        if names is None:
            return
        refresh_controls()
        events = names.accept(samples, source, now=clock, timestamp_ms=timestamp)
        if questions is not None:
            questions.feed(samples)
        if args.command == 'mic' and args.pi:
            from audio.pi_spatial import annotate_events, unknown, window_evidence
            # The spotter fires just after the phrase ends, so the last 1.5 s of frames covers it.
            annotate_events(events, window_evidence(spatial_frames[-15:], require_current=False)
                            if spatial_frames else unknown('speech_window_not_localized'))
        name_decisions.extend(names.decisions)
        deliveries = [{'event_id':e['event_id'],'status':publish(e,args.endpoint)} for e in events]
        name_events.extend(events)
        for event in events if questions is not None else ():
            questions.trigger(event, source)   # after annotate_events, so the question keeps the direction
        if names.decisions:
            decision_log.write(dict(kind='name_detection',source=source,window_timestamp_ms=timestamp,
                decisions=names.decisions,deliveries=deliveries))

    def process(window, source, clock=None, timestamp=None, spatial=None):
        nonlocal snap_latched
        refresh_controls()
        scores, elapsed = model.predict(window)
        if args.debug:
            print(json.dumps({'inference_ms':round(elapsed, 1), 'top5':sorted(scores.items(), key=lambda x:x[1], reverse=True)[:5]}), file=sys.stderr)
        snap = detector.policy['rules'].get('finger_snap')
        if snap is not None:
            # Camera-free experimental input: explicit opt-in, a current target, strong model evidence.
            snap['enabled'] = controls.snap_to_dismiss and controls.active_event_id is not None
            snap['threshold'] = max(0.8, snap['threshold'])
            snap['cooldown_seconds'] = 0.5
        if scores.get('Finger snapping', 0) < 0.4:
            snap_latched = False
        events=detector.detect(scores, source, now=clock, timestamp_ms=timestamp)
        scoped = []
        for event in events:
            if event['type'] == 'finger_snap':
                if snap_latched:
                    continue
                snap_latched = True
                event['target_event_id'] = controls.active_event_id
            scoped.append(event)
        events = scoped
        events += catalog.detect(scores, source, now=clock, timestamp_ms=timestamp)
        custom_decisions=list(catalog.decisions)
        if custom is not None:
            from audio.custom_sounds import rms
            events+=custom.detect(model.last_embedding, rms(window), source, now=clock, timestamp_ms=timestamp)
            custom_decisions += custom.decisions
        if spatial is not None:
            from audio.pi_spatial import annotate_events
            annotate_events(events, spatial, competing=len(events) > 1)
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
                rule_decisions=detector.decisions + name_decisions + (
                    [dict(type="name_called", reason="disabled")] if names is not None and not names.active else []),
                custom_decisions=custom_decisions,
                custom_labels={**{r['id']:r['label'] for r in catalog.rules},
                               **({m['id']:m['label'] for m,_ in custom.heads} if custom is not None else {})},
                events=events_for_observation, top_k=args.observe_top,
                window_seconds=model.window_samples/16000, hop_seconds=model.hop_samples/16000))
        name_decisions.clear()
        decision_log.write(dict(kind='recognition_window',source=source,model=args.model,
            spatial=spatial,
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
        if questions is not None:
            questions.flush()
        return
    # 0.2 s blocks so the name spotter hears speech quickly; sound windows still run every hop.
    block_samples = 1600 if args.pi else (3200 if model.hop_samples % 3200 == 0 else model.hop_samples)
    pending = queue.Queue(maxsize=max(4, 4*model.hop_samples//block_samples))
    def callback(indata, frames, timing, status):
        if status:
            print(f'Audio capture: {status}', file=sys.stderr)
        item = (indata[:, 0].copy(), time.monotonic(), int(time.time()*1000), 0, None)
        try:
            pending.put_nowait(item)
        except queue.Full:
            pending.get_nowait()
            pending.put_nowait(item)
            print('Dropped audio block: processing is behind', file=sys.stderr)
    buffer = np.empty(0, dtype=np.float32)
    last_capture = None
    last_generation = None
    spatial_frames = []
    start = time.monotonic()
    if args.pi:
        from audio.pi_input import PiInput
        capture = PiInput(pending, args.pi, args.pi_device, args.levels_port)
    else:
        import sounddevice as sd
        capture = sd.InputStream(device=args.device, channels=1, samplerate=16000,
                                 blocksize=block_samples, dtype='float32', callback=callback)
    with capture:
        print(f'Audio input: {"Pi stereo " + args.pi if args.pi else "Mac microphone (fallback)"}; '
              'Ctrl+C stops. Raw audio is not saved.', file=sys.stderr)
        while not args.seconds or time.monotonic()-start < args.seconds:
            try:
                block, captured, wall, generation, spatial_frame = pending.get(timeout=3)
            except queue.Empty:
                # OS/device interruptions are not silence and must not terminate recognition.
                if last_capture is not None:
                    print('Audio input paused; waiting for microphone frames to resume.', file=sys.stderr)
                    buffer = np.empty(0, dtype=np.float32)
                    spatial_frames = []
                    if names is not None:
                        names.reset()
                    last_capture = None
                continue
            if time.monotonic() - captured > .5:
                buffer = np.empty(0, dtype=np.float32)
                spatial_frames = []
                if names is not None:
                    names.reset()
                last_capture = None
                continue
            if generation != last_generation or (last_capture is not None and
                    captured-last_capture > 3*block_samples/16000):
                buffer = np.empty(0, dtype=np.float32)
                spatial_frames = []
                if names is not None:
                    names.reset()
            last_generation = generation
            last_capture = captured
            if args.pi:
                spatial_frames.append(spatial_frame)
            hear_names(block, 'microphone', captured, wall, spatial_frames)
            buffer = np.concatenate((buffer, block))
            if len(buffer) >= model.window_samples:
                spatial = None
                if args.pi:
                    from audio.pi_spatial import window_evidence
                    spatial = window_evidence(spatial_frames[-(model.window_samples // block_samples):], require_current=False)
                process(buffer[-model.window_samples:], 'microphone', captured, wall, spatial=spatial)
                buffer = buffer[-(model.window_samples-model.hop_samples):]
                spatial_frames = spatial_frames[-((model.window_samples-model.hop_samples)//block_samples):]

if __name__ == '__main__':
    import signal
    # Noninteractive launchers may inherit SIGINT ignored. Always allow deliberate,
    # graceful worker reloads so PiInput releases its SSH stream and meter port.
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        main()
    except KeyboardInterrupt:
        pass
