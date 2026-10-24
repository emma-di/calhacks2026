"""One-command laptop demo. Defaults to recorded audio; microphone is opt-in."""
import argparse
import errno
from http.server import ThreadingHTTPServer
import json
import subprocess
import sys
import threading
from urllib.request import urlopen
from audio.events import runtime_model
from audio.benchmark import DATA
from audio.server import create_server

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',choices=['replay','mic'],default='replay')
    p.add_argument('--event',choices=['dog_bark','knock','siren','smoke_alarm','alarm_clock','bell'],default='dog_bark')
    p.add_argument('--model',choices=['yamnet','zipformer'],default=runtime_model())
    p.add_argument('--device',type=int)
    p.add_argument('--exit-after-demo',action='store_true')
    args=p.parse_args()
    server=None
    try:
        server=create_server()
        threading.Thread(target=server.serve_forever,daemon=True).start()
    except OSError as exc:
        if exc.errno not in (errno.EADDRINUSE,):
            raise
        with urlopen('http://127.0.0.1:8765/state',timeout=2) as response:
            state=json.load(response)
        if not all(key in state for key in ('active','events')):
            raise RuntimeError('Port 8765 is already used by another service')
    print('Monitor: http://127.0.0.1:8765',flush=True)
    command=[sys.executable,'-m','audio.cli','--model',args.model]
    if args.input=='mic':
        command+=['mic']
        if args.device is not None:
            command+=['--device',str(args.device)]
    else:
        manifest=json.loads((DATA/'manifest.json').read_text())
        target='bicycle_bell' if args.event=='bell' else args.event
        row=next(r for r in manifest['clips'] if r['split']=='tune' and target in r['expected'])
        print(f'Replaying labeled recording: {row["id"]} (no microphone)',flush=True)
        command+=['file',str(DATA/row['path']),'--realtime']
    command+=['--endpoint','http://127.0.0.1:8765/events','--debug']
    try:
        subprocess.run(command,check=True)
        if not args.exit_after_demo:
            print('Replay complete. Monitor stays open; Ctrl+C stops it.',flush=True)
            threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.shutdown()
            server.server_close()

if __name__=='__main__':
    main()
