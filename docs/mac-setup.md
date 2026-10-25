# Move the demo to another Mac

Emma confirmed a separate Mac will run inference. The implementation was tested on Apple Silicon;
record the destination Mac's chip and macOS version before declaring portability verified. Do not copy
this machine's `.venv`, `node_modules`, caches, credentials or absolute paths to another machine.

## Fresh checkout and runtimes

Install Git, Python 3.12 and Node 22.12+ using the team's normal trusted setup. Clone the private repo
with your own GitHub access. Until merge, the complete working snapshot is on `codex/browser-mirror`:

```sh
git clone git@github.com:emma-di/calhacks2026.git
cd calhacks2026
git switch --track origin/codex/browser-mirror
python3.12 --version
node --version
uname -m
```

Run Git commands only in the new checkout; preserve any existing local work. `arm64` and `x86_64`
need compatible package wheels. The full requirements lock is a tested Mac snapshot, not a promise
that a virtual environment can be transferred unchanged across architectures.

## Install dependencies and assets

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-audio.txt
.venv/bin/python -m audio.download_model
.venv/bin/python -m audio.prepare_benchmark --from-manifest reports/dataset-manifest.json
npm ci --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend
.venv/bin/python -m unittest discover -s tests -v
```

Model weights and test recordings are intentionally not in Git. First-run downloads need network
access and space; prepare them before judging. If installation fails on Intel/macOS, inspect that
platform's actual supported wheels before changing shared dependency pins. TensorFlow/YAMNet is optional.

## Recorded smoke test, no microphone

In one terminal:

```sh
.venv/bin/python -m audio.server
```

In a second:

```sh
npm run dev --prefix frontend
```

Open http://127.0.0.1:5173 and choose Receiver. In a third:

```sh
.venv/bin/python -m audio.demo --event smoke_alarm --exit-after-demo
```

Success means a Recording-sourced event appears in the new browser and monochrome preview.
Dismiss the urgent cue before testing lower-priority receiver events. Local simulator buttons are
isolated samples; Play sequence demonstrates competing priorities. Receiver mode retains backend priority.

Both servers bind loopback. The current frontend proxy expects Python on **the same Mac**. Merely
hosting the UI in Mana does not connect it to that Mac. No public tunnel or Pi connection exists yet.

## Later hardware and live test

- Verify microphone permissions and select the actual input device explicitly; no microphone is
  started by the frontend or commands above.
- Pi Wi-Fi/audio ingress and display transport need separate adapters, agreed credentials and a real
  shared-network test. Never just expose the unauthenticated diagnostic receiver on all interfaces.
- Test startup, reconnect, expiry, physical clear, final microphone and end-to-end delay in the room.
- Saved browser drafts/settings do not travel with Git. Export the intended profile; live import/application
  is a separate backend integration checkpoint.

Code, SVGs, bitmap assets and JSON contracts can move. Environment setup, downloaded assets, input
permissions, network transport and physical optics must be validated on the destination system.
