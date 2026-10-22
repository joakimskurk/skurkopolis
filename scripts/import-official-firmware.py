#!/usr/bin/env python3
"""Extract the pinned official rev009+ HEX locally, without executing the updater."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
from inspect_firmware import parse_hex

URL = 'https://intellijel.com/downloads/firmware/Intellijel_Firmware_Updater_macOS_2025-04-17.zip'
ZIP_SHA = '0df68db25d7f4c9d383e775c768684ba9d8e4fc701a1ed4f33d8496b7f304e3a'
MEMBER = 'Intellijel Firmware Updater.app/Contents/Resources/firmware/metropolis_1.37.hex'
HEX_SHA = '996cac09c44112cccf7d89a50cdb600722586c1cd807536730134794dd9569c9'


def import_archive(archive, destination):
    archive, destination = Path(archive), Path(destination)
    if archive.stat().st_size > 20 * 1024 * 1024:
        raise ValueError('Archive exceeds size bound')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ZIP_SHA:
        raise ValueError('Archive differs from the inspected official release; inspect it separately')
    with zipfile.ZipFile(archive) as source:
        entries = [i for i in source.infolist() if i.filename == MEMBER]
        if len(entries) != 1 or entries[0].file_size > 1024 * 1024:
            raise ValueError('Missing, duplicate or oversized firmware member')
        data = source.read(entries[0])
    if hashlib.sha256(data).hexdigest() != HEX_SHA:
        raise ValueError('HEX hash differs from inspected firmware')
    _, metadata = parse_hex(data)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / 'metropolis_1.37.hex'
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError('Existing local firmware differs; refusing overwrite')
    else:
        with target.open('xb') as out:
            out.write(data)
    return {'sourceUrl': URL, 'archiveSha256': ZIP_SHA, 'member': MEMBER,
            'revisionFamily': 'rev009 or higher', 'firmwareVersion': '1.37',
            'output': str(target), **metadata,
            'hardwareWritten': False, 'updaterExecuted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(import_archive(args.archive, ROOT / 'firmware-local'), indent=2))
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
