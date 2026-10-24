"""Download a reproducible, labeled test subset. No microphone access."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import io
import json
import re
from pathlib import Path
import time
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'samples' / 'benchmark'
ESC = 'https://raw.githubusercontent.com/karolpiczak/ESC-50/master/'
ESC_TARGETS = {'dog':'dog_bark', 'door_wood_knock':'knock', 'siren':'siren', 'clock_alarm':'alarm_clock'}

def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent':'CalHacks-audio-evaluation/1'}), timeout=45) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)

def esc_rows():
    metadata = fetch(ESC + 'meta/esc50.csv').decode()
    rows = list(csv.DictReader(io.StringIO(metadata)))
    selected = []
    for category in sorted({r['category'] for r in rows}):
        for fold in range(1, 6):
            group = sorted((r for r in rows if r['category'] == category and int(r['fold']) == fold), key=lambda r:r['filename'])
            # All 40 examples per target; one example per other class per fold.
            for row in group if category in ESC_TARGETS else group[:1]:
                selected.append(dict(id='esc50-' + row['filename'][:-4],
                    path='esc50/' + row['filename'], expected=[ESC_TARGETS[category]] if category in ESC_TARGETS else [],
                    category=category, split='tune' if fold <= 3 else 'test',
                    source='ESC-50', source_group=row['src_file'], fold=fold,
                    url=ESC + 'audio/' + row['filename'],
                    license='CC-BY (ESC-10 subset)' if row['esc10']=='True' else 'CC-BY-NC (ESC-50; inspect upstream LICENSE)'))
    return selected

def supplemental_rows():
    selected, failures = [], []
    sources = [
        ('Kinoton',431320,'bicycle_bell','tune','CC0'),
        ('InspectorJ',484344,'bicycle_bell','test','CC-BY-4.0'),
        ('erihamster',136482,'smoke_alarm','tune','CC0'),
        ('SpliceSound',369847,'smoke_alarm','tune','CC0'),
        ('Garuda1982',530094,'smoke_alarm','test','CC0'),
        ('jess90',680073,'smoke_alarm','test','CC0'),
    ]
    for author, sound_id, kind, split, license in sources:
        page=f'https://freesound.org/people/{author}/sounds/{sound_id}/'
        try:
            html=fetch(page).decode()
            urls=re.findall(r'https://cdn.freesound.org/previews/[^\s"<>]+hq.mp3',html)
            if not urls:
                raise ValueError('No public preview link')
            selected.append(dict(id=f'freesound-{sound_id}',path=f'supplemental/{sound_id}.mp3',
                expected=[kind],category=kind,split=split,source='Freesound public HQ preview',
                source_group=f'freesound-author-{author}',author=author,license=license,
                source_page=page,url=urls[0]))
        except Exception as exc:
            failures.append(f'{page}: {exc}')
    selected.append(dict(id='wikimedia-rotating-bell',path='supplemental/rotating-bell.wav',
        expected=['bicycle_bell'],category='bicycle_bell',split='test',source='Wikimedia Commons',
        source_group='AntumDeluge',author='AntumDeluge',license='CC0',
        source_page='https://commons.wikimedia.org/wiki/File:Rotating-bicycle-bell.wav',
        url='https://upload.wikimedia.org/wikipedia/commons/c/ce/Rotating-bicycle-bell.wav'))
    return selected, failures

def download(row):
    path = DEST / row['path']
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        content = fetch(row['url'])
        temporary = path.with_suffix('.part')
        temporary.write_bytes(content)
        temporary.replace(path)
    result = {k:v for k,v in row.items() if k != 'url'}
    result['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    if row.get('sha256') and result['sha256'] != row['sha256']:
        raise ValueError('Audio checksum differs from recorded manifest')
    result['url'] = row['url']
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--esc-only', action='store_true')
    p.add_argument('--from-manifest',type=Path,help='Reproduce the exact saved source list and SHA256 checksums')
    p.add_argument('--extension',type=Path,help='Append a reviewed, pre-split supplemental source list')
    args = p.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    saved=json.loads(args.from_manifest.read_text()) if args.from_manifest else None
    rows = saved['clips'] if saved else esc_rows()
    notes = saved.get('missing_sources',[]) if saved else []
    if not saved and not args.esc_only:
        more, notes = supplemental_rows()
        rows.extend(more)
    elif not saved:
        notes=['Bicycle bells and smoke alarms excluded by --esc-only']
    if args.extension:
        existing={row['id'] for row in rows}
        rows += [row for row in json.loads(args.extension.read_text())['clips'] if row['id'] not in existing]
    manifest, errors = [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        pending = {pool.submit(download, row):row for row in rows}
        for n, future in enumerate(as_completed(pending), 1):
            try:
                manifest.append(future.result())
            except Exception as exc:
                errors.append({'id':pending[future]['id'], 'error':str(exc)})
            if n%25==0 or n==len(rows):
                print(f'{n}/{len(rows)} downloaded; failures={len(errors)}', flush=True)
    manifest.sort(key=lambda r:r['id'])
    output = dict(version=1, clips=manifest, missing_sources=notes, download_errors=errors,
                  source_notes='ESC-50 upstream folds 1–3 tune / 4–5 test; supplemental sources split by author before inference. Labels not based on predictions.')
    (DEST/'manifest.json').write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({'clips':len(manifest), 'missing_sources':notes, 'download_errors':errors}, indent=2))

if __name__ == '__main__':
    main()
