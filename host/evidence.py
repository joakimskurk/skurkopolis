"""Local evidence bookkeeping and reviewed wiring plans. Never talks to hardware."""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = 'METROPOLIS Main rev010'
FIELDS = ('direction', 'role', 'target_ic', 'target_pin', 'active_level',
          'pull', 'analog_digital', 'interrupt_relevance')
META = ('electronic_signature', 'clock_hz', 'fuses', 'lock_bits')
PORTS = ('PC6', 'PD0', 'PD1', 'PD2', 'PD3', 'PD4', None, None, 'PB6',
         'PB7', 'PD5', 'PD6', 'PD7', 'PB0', 'PB1', 'PB2', 'PB3', 'PB4',
         'PB5', None, None, None, 'PC0', 'PC1', 'PC2', 'PC3', 'PC4', 'PC5')
KINDS = {'continuity', 'pcb_trace', 'passive_capture', 'device_readout'}


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=strict_object,
                      parse_constant=lambda s: (_ for _ in ()).throw(EvidenceError('Invalid JSON number: ' + s)))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def timestamp(value):
    require(isinstance(value, str), 'Timestamp must be an ISO 8601 string')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise EvidenceError('Invalid timestamp: ' + value) from exc
    require(parsed.tzinfo is not None, 'Timestamp must include a timezone')


def text_field(value, name):
    require(isinstance(value, str) and bool(value.strip()), name + ' must be nonempty text')


def local_artifact(root, name):
    require(isinstance(name, str) and bool(name), 'Artifact path missing')
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Artifact must use a confined relative path')
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), 'Artifact escapes project root')
    require(path.is_file(), 'Missing evidence file: ' + name)
    return path


def check_registry(root, registry):
    require(isinstance(registry, dict) and registry.get('schema') == 1, 'Unsupported evidence schema')
    require(registry.get('board') == BOARD, 'Evidence board mismatch')
    require(isinstance(registry.get('records'), list), 'Evidence records must be a list')
    records = {}
    for record in registry['records']:
        require(isinstance(record, dict), 'Evidence record must be an object')
        rid = record.get('id')
        require(isinstance(rid, str) and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', rid), 'Invalid evidence id')
        require(rid not in records, 'Duplicate evidence id: ' + rid)
        require(record.get('board') == BOARD, rid + ': board mismatch')
        require(record.get('kind') in KINDS, rid + ': unsupported evidence kind')
        require(record.get('status') in ('pending', 'reviewed'), rid + ': invalid review status')
        timestamp(record.get('observed_at'))
        text_field(record.get('operator'), rid + ' operator')
        text_field(record.get('notes'), rid + ' notes')
        artifacts = record.get('artifacts')
        require(isinstance(artifacts, list) and len(artifacts) > 0, rid + ': no artifacts')
        for artifact in artifacts:
            require(isinstance(artifact, dict), rid + ': invalid artifact')
            expected = artifact.get('sha256')
            require(isinstance(expected, str) and re.fullmatch(r'[0-9a-f]{64}', expected), rid + ': invalid SHA-256')
            require(sha256(local_artifact(root, artifact.get('path'))) == expected, rid + ': artifact hash mismatch')
        claims = record.get('claims')
        require(isinstance(claims, list), rid + ': claims must be a list')
        for claim in claims:
            require(isinstance(claim, dict), rid + ': claim must be an object')
            if 'pin' in claim:
                require(set(claim) == {'pin', 'fields'} and claim['pin'] in {str(n) for n in range(1, 29)}, rid + ': invalid pin claim')
                require(isinstance(claim['fields'], dict) and bool(claim['fields']), rid + ': empty pin claim')
                require(set(claim['fields']).issubset(FIELDS), rid + ': unsupported pin field')
                for value in claim['fields'].values():
                    require(value is not None, rid + ': cannot certify an unknown value')
            else:
                require(set(claim) == {'field', 'value'} and claim['field'] in META, rid + ': invalid metadata claim')
                require(claim['value'] is not None, rid + ': cannot certify an unknown value')
        if record['status'] == 'reviewed':
            text_field(record.get('reviewer'), rid + ' reviewer')
            timestamp(record.get('reviewed_at'))
            require(bool(claims), rid + ': reviewed record needs explicit claims')
        records[rid] = record
    return records


def same(a, b):
    # bool is a subclass of int in Python, but not an interchangeable measurement.
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return set(a) == set(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def resolve_refs(refs, records, where):
    require(isinstance(refs, list) and all(isinstance(x, str) for x in refs), where + ': invalid evidence references')
    require(len(refs) == len(set(refs)), where + ': duplicate evidence references')
    result = []
    for rid in refs:
        require(rid in records, where + ': unknown evidence ' + rid)
        require(records[rid]['status'] == 'reviewed', where + ': evidence not reviewed: ' + rid)
        result.append(records[rid])
    return result


def validate(root=ROOT):
    root = Path(root)
    board = read_json(root / 'specs/hardware-map.yaml')
    registry = read_json(root / 'specs/evidence-registry.json')
    records = check_registry(root, registry)
    contracts = read_json(root / 'specs/rev010-peripheral-contracts.json')
    require(contracts.get('board') == BOARD, 'Peripheral contracts board mismatch')
    for candidate in contracts['candidates']:
        require(candidate['mcu_pins'] == [] and candidate['board_role_status'] in ('candidate only', 'unknown'),
                'Generic contracts must not carry board mappings; use the evidence-backed map')
    require(board.get('schema') == 3 and board.get('board') == BOARD, 'Unsupported board map')
    require(board.get('mcu_marking') == 'ATMEGA328-PU' and board.get('datasheet_signature') == '1e9514', 'MCU identity mismatch')
    require(board.get('policy') == 'no hardware writes', 'Unexpected hardware policy')
    pins = board.get('pins')
    require(isinstance(pins, dict) and set(pins) == {str(n) for n in range(1, 29)}, 'Expected exact PDIP pins 1..28')
    bindings = []
    for number, row in pins.items():
        require(isinstance(row, dict), 'Invalid pin row: ' + number)
        require(row.get('port_bit') == PORTS[int(number)-1], 'Fixed MCU pin identity changed: ' + number)
        require(all(key in row for key in FIELDS), 'Incomplete pin row: ' + number)
        refs = resolve_refs(row.get('evidence'), records, 'pin ' + number)
        assigned = {key: row[key] for key in FIELDS if row[key] is not None}
        for key, value in assigned.items():
            text_field(value, 'pin ' + number + '.' + key)
        if row['direction'] is not None:
            require(row['direction'] in ('input', 'output', 'bidirectional'), 'Invalid MCU direction on pin ' + number)
        if row['analog_digital'] is not None:
            require(row['analog_digital'] in ('analog', 'digital'), 'Invalid signal type on pin ' + number)
        if not assigned:
            require(not refs and row.get('confidence') == 'unmapped' and row.get('verification') == 'not traced', 'Empty pin has a verification claim: ' + number)
            continue
        require(refs and row.get('confidence') == 'verified' and row.get('verification') == 'verified', 'Pin assignment requires reviewed, verified evidence: ' + number)
        for key, value in assigned.items():
            claims = [c['fields'][key] for r in refs for c in r['claims']
                      if c.get('pin') == number and key in c['fields']]
            require(claims and all(same(value, c) for c in claims), 'Missing or conflicting evidence for pin ' + number + '.' + key)
        for record in refs:
            require(any(c.get('pin') == number for c in record['claims']), 'Unrelated evidence attached to pin ' + number)
        if all(row[k] is not None for k in ('role', 'direction', 'target_ic', 'target_pin', 'analog_digital')):
            for key in ('role', 'target_ic', 'target_pin'):
                text_field(row[key], 'pin ' + number + ' ' + key)
            require(row['direction'] in ('input', 'output', 'bidirectional'), 'Invalid MCU direction on pin ' + number)
            require(row['analog_digital'] in ('analog', 'digital'), 'Invalid signal type on pin ' + number)
            bindings.append(dict(pin=number, port_bit=row['port_bit'], **assigned, evidence=row['evidence']))
    metadata_refs = board.get('metadata_evidence')
    require(isinstance(metadata_refs, dict) and set(metadata_refs) == set(META), 'Expected metadata evidence slots')
    for field in META:
        value = board.get(field)
        refs = resolve_refs(metadata_refs[field], records, field)
        if value is None:
            require(not refs, 'Unknown metadata has evidence: ' + field)
            continue
        claims = [c['value'] for r in refs for c in r['claims'] if c.get('field') == field]
        require(claims and all(same(value, c) for c in claims), 'Missing or conflicting evidence for ' + field)
        if field == 'electronic_signature':
            require(value == board['datasheet_signature'], 'Measured MCU signature does not match target; investigate before binding')
        if field == 'clock_hz':
            require(type(value) is int and 0 < value <= 20000000, 'Invalid measured clock')
        if field == 'lock_bits':
            require(type(value) is int and 0 <= value <= 255, 'Invalid lock byte')
        if field == 'fuses':
            require(isinstance(value, dict) and set(value) == {'low', 'high', 'extended'} and
                    all(type(v) is int and 0 <= v <= 255 for v in value.values()), 'Invalid fuse bytes')
    # Detect contradictory reviewed claims even when one has not been attached to a pin.
    seen = {}
    for record in records.values():
        if record['status'] != 'reviewed':
            continue
        for claim in record['claims']:
            pairs = [((claim['pin'], k), v) for k, v in claim['fields'].items()] if 'pin' in claim else [(('metadata', claim['field']), claim['value'])]
            for key, value in pairs:
                require(key not in seen or same(seen[key], value), 'Conflicting reviewed evidence: ' + '.'.join(key))
                seen[key] = value
    return board, records, bindings


def report(root=ROOT, roles=()):
    board, records, bindings = validate(root)
    require(all(isinstance(role, str) and role.strip() for role in roles), 'Invalid required role')
    require(len(set(roles)) == len(roles), 'Duplicate requested roles')
    selected = []
    missing = []
    for role in roles:
        matches = [b for b in bindings if b['role'] == role]
        require(len(matches) <= 1, 'Ambiguous role: ' + role)
        if not matches:
            missing.append(role)
        else:
            require(matches[0]['port_bit'] is not None, 'Cannot bind a power/reference pin as GPIO: ' + role)
            require(matches[0]['pin'] not in ('1', '9', '10'), 'Reset/clock pins need a separate fuse-aware adapter: ' + role)
            require(matches[0]['analog_digital'] == 'digital', 'Analog route needs an analog adapter: ' + role)
            selected.append(matches[0])
    unknown_meta = [field for field in META if board[field] is None]
    return {'schema': 1, 'board': BOARD, 'metadataValid': True,
            'inputs': {'hardwareMapSha256': sha256(Path(root) / 'specs/hardware-map.yaml'),
                       'registrySha256': sha256(Path(root) / 'specs/evidence-registry.json')},
            'reviewedRecords': sum(r['status'] == 'reviewed' for r in records.values()),
            'pendingRecords': sum(r['status'] == 'pending' for r in records.values()),
            'assignedPins': sum(any(row[k] is not None for k in FIELDS) for row in board['pins'].values()),
            'completeBindings': len(bindings), 'missingMetadata': unknown_meta,
            'requestedRoles': list(roles), 'missingRoles': missing, 'bindings': selected,
            'bindingArtifacts': {rid: records[rid]['artifacts'] for rid in
                                 sorted({rid for b in selected for rid in b['evidence']})},
            'wiringSubsetReady': bool(roles) and not missing,
            'boardEmulated': False, 'originalFirmwareRunnable': False,
            'limitations': ['Checks recorded evidence consistency, not measurement truth.',
                            'A wiring plan does not attach simavr or qualify peripheral timing.',
                            'Scope is the explicitly requested digital roles only.']}


def register(root, source, rid, kind, observed_at, operator, notes):
    root, source = Path(root), Path(source)
    validate(root)  # Fail before writing when the project is already inconsistent.
    require(source.is_file(), 'Evidence source is not a file')
    require(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', rid), 'Invalid evidence id')
    require(kind in KINDS, 'Unsupported evidence kind')
    timestamp(observed_at)
    text_field(operator, 'operator')
    text_field(notes, 'notes')
    registry_path = root / 'specs/evidence-registry.json'
    lock = registry_path.with_suffix('.lock')
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise EvidenceError('Evidence registry is locked; inspect the other writer before retrying') from exc
    copied = None
    staged = None
    try:
        os.close(handle)
        registry = read_json(registry_path)
        require(all(r['id'] != rid for r in registry['records']), 'Evidence id already exists: ' + rid)
        folder = root / 'evidence/local'
        folder.mkdir(parents=True, exist_ok=True)
        require(folder.resolve().is_relative_to(root.resolve()), 'Evidence folder escapes project root')
        destination = folder / (rid + '.bin')
        require(not destination.exists(), 'Evidence destination exists')
        # Exclusive creation also prevents overwrite if another writer races this check.
        with source.open('rb') as src, destination.open('xb') as dst:
            copied = destination
            for chunk in iter(lambda: src.read(1024 * 1024), b''):
                dst.write(chunk)
        record = {'id': rid, 'board': BOARD, 'kind': kind, 'status': 'pending',
                  'observed_at': observed_at, 'operator': operator, 'notes': notes,
                  'original_name': source.name,
                  'artifacts': [{'path': copied.relative_to(root).as_posix(), 'sha256': sha256(copied)}],
                  'claims': []}
        registry['records'].append(record)
        check_registry(root, registry)
        with tempfile.NamedTemporaryFile(mode='w', dir=registry_path.parent, delete=False) as tmp:
            staged = Path(tmp.name)
            json.dump(registry, tmp, indent=2)
            tmp.write('\n')
        os.replace(staged, registry_path)
        copied = None  # committed; cleanup must not delete evidence
        return record
    finally:
        if copied is not None and copied.is_file():
            copied.unlink()
        if staged is not None and staged.exists():
            staged.unlink()
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    plan = sub.add_parser('plan')
    plan.add_argument('--roles', nargs='+', required=True, help='Exact role labels to require; never inferred from IC names')
    ingest = sub.add_parser('register')
    ingest.add_argument('source', type=Path)
    ingest.add_argument('--id', required=True)
    ingest.add_argument('--kind', choices=sorted(KINDS), required=True)
    ingest.add_argument('--observed-at', required=True)
    ingest.add_argument('--operator', required=True)
    ingest.add_argument('--notes', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'register':
            output = register(args.root, args.source, args.id, args.kind, args.observed_at, args.operator, args.notes)
            code = 0
        else:
            output = report(args.root, getattr(args, 'roles', ()))
            code = 2 if args.command == 'plan' and not output['wiringSubsetReady'] else 0
        print(json.dumps(output, indent=2))
        return code
    except (EvidenceError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc), 'wiringSubsetReady': False, 'boardEmulated': False}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
