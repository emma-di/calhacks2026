"""Download the official Zipformer release and safely extract into project cache."""
import hashlib
import json
from pathlib import Path
import tarfile
from urllib.request import urlopen
from audio.model import ROOT

NAME='sherpa-onnx-zipformer-small-audio-tagging-2024-04-15'
URL=f'https://github.com/k2-fsa/sherpa-onnx/releases/download/audio-tagging-models/{NAME}.tar.bz2'

def main():
    cache=ROOT/'.cache'
    cache.mkdir(exist_ok=True)
    archive=cache/'zipformer.tar.bz2'
    if not archive.exists():
        temporary=archive.with_suffix('.part')
        with urlopen(URL,timeout=90) as response, temporary.open('wb') as output:
            while block:=response.read(1024*1024):
                output.write(block)
        temporary.replace(archive)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    expected_file=Path(__file__).with_name('model-assets.json')
    if expected_file.exists():
        expected=json.loads(expected_file.read_text())['zipformer_archive_sha256']
        if digest!=expected:
            raise RuntimeError('Model archive checksum mismatch')
    with tarfile.open(archive) as package:
        package.extractall(cache/'models', filter='data')
    print(f'Zipformer ready. Archive SHA256: {digest}')

if __name__=='__main__':
    main()
