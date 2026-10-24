"""Download official sherpa-onnx releases and safely extract into the project cache.

    python -m audio.download_model            # sound classifier (Zipformer audio tagging)
    python -m audio.download_model --names    # also the name-detection keyword spotter
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
from urllib.request import urlopen
from audio.model import ROOT

RELEASES = 'https://github.com/k2-fsa/sherpa-onnx/releases/download'
MODELS = {
    'zipformer': ('sherpa-onnx-zipformer-small-audio-tagging-2024-04-15', 'audio-tagging-models', 'zipformer_archive_sha256'),
    'names': ('sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01', 'kws-models', 'kws_archive_sha256'),
}
NAME = MODELS['zipformer'][0]
URL = f'{RELEASES}/audio-tagging-models/{NAME}.tar.bz2'

def fetch(kind):
    name, release, checksum_key = MODELS[kind]
    cache = ROOT/'.cache'
    cache.mkdir(exist_ok=True)
    archive = cache/('zipformer.tar.bz2' if kind == 'zipformer' else f'{name}.tar.bz2')
    if not archive.exists():
        temporary = archive.with_suffix('.part')
        with urlopen(f'{RELEASES}/{release}/{name}.tar.bz2', timeout=90) as response, temporary.open('wb') as output:
            while block := response.read(1024*1024):
                output.write(block)
        temporary.replace(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    expected_file = Path(__file__).with_name('model-assets.json')
    if expected_file.exists():
        expected = json.loads(expected_file.read_text()).get(checksum_key)
        if expected and digest != expected:
            raise RuntimeError(f'{kind} model archive checksum mismatch')
    with tarfile.open(archive) as package:
        package.extractall(cache/'models', filter='data')
    print(f'{kind} model ready. Archive SHA256: {digest}')

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--names', action='store_true', help='also download the name-detection model (~17 MB)')
    args = parser.parse_args()
    fetch('zipformer')
    if args.names:
        fetch('names')

if __name__ == '__main__':
    main()
