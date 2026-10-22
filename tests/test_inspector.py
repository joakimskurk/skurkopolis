import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inspect_firmware', ROOT/'host/inspect_firmware.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def record(address, kind, data=b''):
    raw = bytes([len(data), address >> 8, address & 255, kind]) + data
    return ':' + (raw + bytes([-sum(raw) & 255])).hex().upper() + '\n'


def program(data=b'\xff\xcf'):
    # Our own two-byte AVR RJMP -1 program. No proprietary firmware fixture.
    return (record(0, 0, data) + record(0, 1)).encode()


class HexTests(unittest.TestCase):
    def test_decode_and_pad(self):
        image, info = mod.parse_hex(program())
        self.assertEqual(len(image), 32768)
        self.assertEqual(image[:2], b'\xff\xcf')
        self.assertEqual(image[2:], b'\xff'*32766)
        self.assertEqual(info['populatedBytes'], 2)
    def test_checksum_and_length(self):
        for data in (b':02000000FFCF31\n:00000001FF\n', b':03000000FFCF30\n:00000001FF\n'):
            with self.assertRaises(ValueError): mod.parse_hex(data)
    def test_overlap_and_out_of_bounds(self):
        for data in (record(0,0,b'12')+record(1,0,b'3'), record(0x8000,0,b'12')):
            with self.assertRaises(ValueError): mod.parse_hex((data+record(0,1)).encode())
    def test_extended_address_escape(self):
        for kind in (2,4):
            with self.assertRaises(ValueError):
                mod.parse_hex((record(0,kind,b'\x10\x00')+record(0,0,b'12')+record(0,1)).encode())
    def test_zero_extended_address(self):
        raw=(record(0,4,b'\x00\x00')+record(0,0,b'12')+record(0,1)).encode()
        self.assertEqual(mod.parse_hex(raw)[0][:2],b'12')
    def test_eof_and_reset_requirements(self):
        for data in (record(0,0,b'12'), record(2,0,b'12')+record(0,1), record(0,1), program().decode()+record(0,1)):
            with self.assertRaises(ValueError): mod.parse_hex(data.encode())
    def test_unsupported_and_malformed(self):
        for data in (record(0,5,b'\x00'*4).encode()+program(), b':GG\n', b'\xff', b':00 000001FF\n', b'x'*1048577):
            with self.assertRaises(ValueError): mod.parse_hex(data)
    def test_invalid_eof_and_extended_shape(self):
        for line in (record(1,1),record(0,1,b'1'),record(1,4,b'12'),record(0,2,b'1')):
            with self.assertRaises(ValueError): mod.parse_hex(line.encode()+program())


@unittest.skipUnless(os.environ.get('RUN_CPU_TESTS')=='1','CPU inspector build required')
class CpuTests(unittest.TestCase):
    def test_known_loop_deterministic(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'loop.hex';p.write_bytes(program())
            a=mod.inspect(p,ROOT/'build/cpu_inspector',10000)
            b=mod.inspect(p,ROOT/'build/cpu_inspector',10000)
            self.assertEqual(a,b)
            s=a['simulation']
            self.assertEqual(s['cycles'],10000)
            self.assertEqual(s['finalPc'],0)
            self.assertEqual(s['topPcSamples'],[{'byteAddress':0,'samples':5000}])
            self.assertFalse(s['boardEmulated'])
    def test_observes_known_port_change(self):
        # LDI r16,0x20; OUT DDRB,r16; RJMP -1, hand-assembled synthetic test.
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'gpio.hex';p.write_bytes(program(bytes.fromhex('00e204b9ffcf')))
            r=mod.inspect(p,ROOT/'build/cpu_inspector',10000)
            d=next(x for x in r['simulation']['registers'] if x['name']=='DDRB')
            self.assertEqual(d['finalValue'],0x20)
            self.assertEqual(d['observedChanges'],1)
    def test_bad_raw_length_rejected(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(b'bad');f.flush()
            p=subprocess.run([str(ROOT/'build/cpu_inspector'),f.name,'100','16000000'],capture_output=True)
            self.assertEqual(p.returncode,1)
    def test_invalid_budget_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'loop.hex';p.write_bytes(program())
            for cycles in (0,100000001,True):
                with self.assertRaises(ValueError): mod.inspect(p,ROOT/'build/cpu_inspector',cycles)


if __name__=='__main__': unittest.main()
