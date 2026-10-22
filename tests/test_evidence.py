"""Synthetic bookkeeping fixtures, never measurements of the user's rev010."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('evidence', ROOT / 'host/evidence.py')
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'specs').mkdir()
        for name in ('hardware-map.yaml', 'evidence-registry.json', 'rev010-peripheral-contracts.json'):
            shutil.copyfile(ROOT / 'specs' / name, self.root / 'specs' / name)
        self.map = ev.read_json(self.root / 'specs/hardware-map.yaml')
        self.registry = {'schema': 1, 'board': ev.BOARD, 'records': []}
        self.source = self.root / 'test-only.txt'
        self.source.write_text('SYNTHETIC TEST DATA. NOT A REAL BOARD OBSERVATION.\n')
    def save(self):
        (self.root / 'specs/hardware-map.yaml').write_text(json.dumps(self.map))
        (self.root / 'specs/evidence-registry.json').write_text(json.dumps(self.registry))
    def fixture(self, pin='17', role='fixture.output', status='reviewed'):
        fields = dict(role=role, direction='output', target_ic='SYNTHETIC_ONLY', target_pin='TEST_INPUT', analog_digital='digital')
        record = dict(id='synthetic-test', board=ev.BOARD, kind='continuity', status=status,
            observed_at='2026-10-18T12:00:00Z', operator='test fixture', notes='Not real evidence',
            reviewed_at='2026-10-18T12:05:00Z', reviewer='test fixture',
            artifacts=[{'path': self.source.name, 'sha256': ev.sha256(self.source)}],
            claims=[{'pin': pin, 'fields': fields.copy()}])
        self.registry['records'].append(record)
        self.map['pins'][pin].update(fields, confidence='verified', verification='verified', evidence=[record['id']])
        self.save()
        return record
    def rejected(self, pattern='.'):
        self.save()
        with self.assertRaisesRegex(ev.EvidenceError, pattern): ev.validate(self.root)
    def test_blank_board_not_ready(self):
        result = ev.report(self.root, ['fixture.output'])
        self.assertEqual(result['assignedPins'], 0)
        self.assertEqual(result['missingRoles'], ['fixture.output'])
        self.assertFalse(result['wiringSubsetReady'])
        self.assertFalse(ev.report(self.root)['wiringSubsetReady'])
    def test_reviewed_subset_plan(self):
        self.fixture()
        result = ev.report(self.root, ['fixture.output'])
        self.assertTrue(result['wiringSubsetReady'])
        self.assertEqual(result['bindings'][0]['port_bit'], 'PB3')
        self.assertFalse(result['boardEmulated'])
        self.assertFalse(result['originalFirmwareRunnable'])
        self.assertFalse(ev.report(self.root, ['fixture.output', 'fixture.other'])['wiringSubsetReady'])
    def test_arbitrary_reference(self):
        self.map['pins']['17'].update(role='fixture.output', evidence=['made-up'], confidence='verified', verification='verified')
        self.rejected('unknown evidence')
    def test_pending_reference(self):
        self.fixture(status='pending')
        self.rejected('not reviewed')
    def test_tampered_missing_artifact(self):
        self.fixture()
        self.source.write_text('changed')
        self.rejected('hash mismatch')
        self.source.unlink()
        self.rejected('Missing evidence file')
    def test_wrong_pin_evidence(self):
        self.fixture()['claims'][0]['pin'] = '18'
        self.rejected('Missing or conflicting')
    def test_each_field_supported(self):
        self.fixture()
        self.map['pins']['17']['active_level'] = 'high'
        self.rejected('active_level')
    def test_unattached_conflicting_record(self):
        record = copy.deepcopy(self.fixture())
        record['id'] = 'conflict'
        record['claims'][0]['fields']['target_pin'] = 'OTHER'
        self.registry['records'].append(record)
        self.rejected('Conflicting reviewed evidence')
    def test_path_and_symlink_escape(self):
        record = self.fixture()
        record['artifacts'][0]['path'] = '../outside'
        self.rejected('confined')
        (self.root / 'escape').symlink_to('/etc/hosts')
        record['artifacts'][0]['path'] = 'escape'
        self.rejected('escapes')
    def test_duplicate_ids_and_json_keys(self):
        self.registry['records'].append(copy.deepcopy(self.fixture()))
        self.rejected('Duplicate evidence id')
        (self.root / 'duplicate.json').write_text('{"a":1,"a":2}')
        with self.assertRaisesRegex(ev.EvidenceError, 'Duplicate JSON key'): ev.read_json(self.root/'duplicate.json')
    def test_fixed_identity(self):
        self.map['pins']['17']['port_bit'] = 'PB4'
        self.rejected('identity changed')
    def test_unsupported_clock(self):
        self.map['clock_hz'] = 16000000
        self.rejected('clock_hz')
    def test_measured_signature_mismatch(self):
        record = self.fixture()
        record['claims'].append({'field':'electronic_signature', 'value':'1e950f'})
        self.map['electronic_signature'] = '1e950f'
        self.map['metadata_evidence']['electronic_signature'] = [record['id']]
        self.rejected('signature does not match')
    def test_power_clock_reset_not_gpio(self):
        for pin in ('7', '9', '1'):
            with self.subTest(pin=pin):
                self.map = ev.read_json(ROOT / 'specs/hardware-map.yaml')
                self.registry['records'] = []
                self.fixture(pin=pin)
                with self.assertRaises(ev.EvidenceError): ev.report(self.root, ['fixture.output'])
    def test_register_preserves_bytes_pending_and_duplicate(self):
        record = ev.register(self.root, self.source, 'readout', 'device_readout', '2026-10-18T12:00:00Z', 'test', 'synthetic readout')
        artifact = self.root / record['artifacts'][0]['path']
        self.assertEqual(artifact.read_bytes(), self.source.read_bytes())
        self.assertEqual(record['status'], 'pending')
        self.assertEqual(record['claims'], [])
        self.assertEqual(ev.report(self.root)['pendingRecords'], 1)
        before = (self.root / 'specs/evidence-registry.json').read_bytes()
        with self.assertRaisesRegex(ev.EvidenceError, 'already exists'):
            ev.register(self.root, self.source, 'readout', 'device_readout', '2026-10-18T12:00:00Z', 'test', 'duplicate')
        self.assertEqual((self.root / 'specs/evidence-registry.json').read_bytes(), before)
        self.assertTrue(artifact.exists())
    def test_existing_destination_preserved(self):
        folder = self.root / 'evidence/local'
        folder.mkdir(parents=True)
        (folder / 'existing.bin').write_bytes(b'keep me')
        with self.assertRaisesRegex(ev.EvidenceError, 'destination exists'):
            ev.register(self.root, self.source, 'existing', 'continuity', '2026-10-18T12:00:00Z', 'test', 'test')
        self.assertEqual((folder / 'existing.bin').read_bytes(), b'keep me')
    def test_optimized_python_keeps_guards(self):
        self.map['pins']['17']['role'] = 'unevidenced'
        self.save()
        proc = subprocess.run([sys.executable, '-O', str(ROOT/'host/evidence.py'), '--root', str(self.root), 'status'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(json.loads(proc.stderr)['wiringSubsetReady'])
    def test_blocked_cli_exit(self):
        proc = subprocess.run([sys.executable, str(ROOT/'host/evidence.py'), '--root', str(self.root), 'plan', '--roles', 'fixture.missing'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)['missingRoles'], ['fixture.missing'])
    def test_analog_not_a_digital_plan(self):
        record = self.fixture(pin='23')
        record['claims'][0]['fields']['analog_digital'] = 'analog'
        self.map['pins']['23']['analog_digital'] = 'analog'
        self.save()
        with self.assertRaisesRegex(ev.EvidenceError, 'Analog route'):
            ev.report(self.root, ['fixture.output'])
    def test_review_requires_named_reviewer_and_timezone(self):
        record = self.fixture()
        record['reviewer'] = ''
        self.rejected('reviewer')
        record['reviewer'] = 'test'
        record['reviewed_at'] = '2026-10-18T12:00:00'
        self.rejected('timezone')
    def test_ambiguous_role_cannot_plan(self):
        record = copy.deepcopy(self.fixture())
        record['id'] = 'other-pin'
        record['claims'][0]['pin'] = '18'
        self.registry['records'].append(record)
        self.map['pins']['18'].update(record['claims'][0]['fields'], confidence='verified', verification='verified', evidence=[record['id']])
        self.save()
        with self.assertRaisesRegex(ev.EvidenceError, 'Ambiguous role'):
            ev.report(self.root, ['fixture.output'])
    def test_ingest_lock_is_respected(self):
        lock = self.root / 'specs/evidence-registry.lock'
        lock.write_text('another writer')
        with self.assertRaisesRegex(ev.EvidenceError, 'locked'):
            ev.register(self.root, self.source, 'readout', 'continuity', '2026-10-18T12:00:00Z', 'test', 'test')
        self.assertEqual(lock.read_text(), 'another writer')
        self.assertFalse((self.root / 'evidence/local').exists())
    def test_wrong_board_record_rejected(self):
        self.fixture()['board'] = 'different revision'
        self.rejected('board mismatch')
if __name__ == '__main__': unittest.main()
