# Working together

Use **one branch per task** and a pull request into `main`. Keep `main` runnable for the demo.
Everyone has write access after accepting their GitHub invitation; nobody needs a fork.

Commit and push each coherent, verified working slice so teammates can follow progress. You do not
need to wait for an entire feature. Keep experimental or broken checkpoints on clearly labeled draft
branches, and never commit credentials, recordings or model weights. Update WORK-STATUS.md when a
milestone changes; pushed branch work is not necessarily merged into main.

## First time

Accept your repo invitation, then:

```sh
gh repo clone emma-di/calhacks2026
cd calhacks2026
git switch -c yourname/short-task-name
```

Examples: `yameens/oled-transport`, `johnaou/name-detection`, `lragogna/onboarding`.
These are naming examples, not assigned tasks.

## Make a change

```sh
git status
# Edit your files, then stage only the files for your task.
git add path/to/changed-file
git commit -m "Describe the behavior you changed"
git push -u origin HEAD
gh pr create --base main
```

Use GitHub's **Compare & pull request** button if you prefer the browser.
Explain the change and how you tested it. Ask a teammate to review before merging;
the Python checks run automatically. This is a team convention, not enforced branch protection.

## Bring main into your branch

Commit or stash your current work first, then:

```sh
git fetch origin
git merge origin/main
```

Resolve conflicts on your task branch. Avoid rewriting someone else's branch history or
force-pushing `main`. After merging a PR, update `main` and start a new branch for the next task.

## Where to work

See [team workstreams](docs/team-workstreams.md). Existing code is intentionally small:

| Area | Current files / proposed home |
| --- | --- |
| Audio recognition | `audio/model.py`, `audio/events.py`, `audio/cli.py` |
| Priority + event receiver | `audio/server.py` |
| Laptop cue UI | `audio/monitor.html` |
| Onboarding + name contract | `docs/name-detection-plan.md`, `docs/onboarding-profile.example.json` |
| Evaluation | `audio/benchmark.py`, `audio/simulate.py`, `reports/` |
| Hardware / spatial / full frontend | Create `hardware/`, `spatial/`, or `frontend/` as that implementation begins |

Before changing the event schema or settings contract, mention it in your PR and coordinate
with the owners of the receiver, display and recognition workers. Keep existing clients working
or document the migration. Treat the name-detection profile as **proposed**, not already implemented.

## Checks

The fast checks need Python 3.12 and NumPy, with no weights, recordings, or microphone:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install 'numpy<3'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q audio
```

If you installed the full audio dependencies, use that same environment instead.
For model/policy changes, also run the relevant recorded-audio benchmark and include measured
before/after results. For UI changes, verify mock events visibly. For hardware changes, document
the transport and how to exercise it with a mock event.

## Keep the repo small

- Commit source, tests, documentation, policy files and intentional evaluation reports.
- Keep model weights, audio recordings, virtual environments, decision logs and credentials out of Git.
- Download fixtures using the saved manifests; preserve source attribution and checksums.
- Regenerate large evaluation reports only when your task changes the evaluation or recognition behavior.
- `requirements.lock.txt` is a snapshot of the tested Apple Silicon environment. Change dependencies
  deliberately rather than committing an unrelated `pip freeze`.
