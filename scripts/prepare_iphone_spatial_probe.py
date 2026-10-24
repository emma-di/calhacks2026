"""Download Apple's project shell and overlay Aware's experimental FOA probe.

No installation, signing, microphone access, recording, or uploads occur here.
Apple's sample license is retained in the generated project. Outputs stay gitignored.
"""
import argparse
import io
from pathlib import Path
import plistlib
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_URL = 'https://docs-assets.developer.apple.com/published/884affb07a9b/CapturingSpatialAudioInYourIOSApp.zip'


def prepare(destination):
    destination = destination.resolve()
    if destination.exists():
        raise ValueError(f'{destination} already exists; refusing to overwrite signing or local changes')
    with urllib.request.urlopen(SAMPLE_URL, timeout=30) as response:
        data = response.read(5_000_001)
    if len(data) > 5_000_000:
        raise ValueError('Sample archive unexpectedly large')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if sum(item.file_size for item in archive.infolist()) > 20_000_000:
            raise ValueError('Expanded sample unexpectedly large')
        for item in archive.infolist():
            if not (destination / item.filename).resolve().is_relative_to(destination):
                raise ValueError('Unsafe archive path')
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Sample symlink not allowed')
        archive.extractall(destination)
    source = ROOT / 'native/PhoneSpatialProbe'
    app = destination / 'SpatialAudioDemo'
    project = destination / 'SpatialAudioDemo.xcodeproj/project.pbxproj'
    if not project.exists() or not (destination / 'LICENSE.txt').exists():
        raise ValueError('Unexpected Apple project layout')
    # Reuse existing project file references. The other sample source files remain licensed but unused.
    (app / 'AudioRecorder.swift').write_text(
        (source / 'FOADirection.swift').read_text() + '\n' + (source / 'ProbeController.swift').read_text())
    shutil.copyfile(source / 'ContentView.swift', app / 'ContentView.swift')
    (app / 'AudioVisualizerView.swift').write_text('// Unused in Aware probe. See LICENSE.txt for the Apple project shell.\n')
    text = project.read_text().replace(
        'com.example.apple-samplecode.SpatialAudioDemo${SAMPLE_CODE_DISAMBIGUATOR}',
        'com.aware.hackathon.SpatialProbe${SAMPLE_CODE_DISAMBIGUATOR}')
    text = text.replace('Spatial Audio Demo Application would like to use the microphone to record audio.',
                        'Test spatial microphone channels for eight seconds. No audio is saved or uploaded.')
    project.write_text(text)
    plist = app / 'Info.plist'
    info = plistlib.loads(plist.read_bytes())
    info['NSMicrophoneUsageDescription'] = 'Test spatial microphone channels for eight seconds. No audio is saved or uploaded.'
    plist.write_bytes(plistlib.dumps(info))
    print(destination / 'SpatialAudioDemo.xcodeproj')
    print('Open in Xcode, select your signing team and physical iPhone. No capture starts until tapped.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT / '.cache/iphone-spatial-probe')
    args = parser.parse_args()
    prepare(args.destination)


if __name__ == '__main__':
    main()
