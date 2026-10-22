import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'host'/f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


inspect = module('inspect_firmware')
analysis = module('analyze_bus')


def hex_program(words):
    data = b''.join(w.to_bytes(2, 'little') for w in words)
    lines = []
    for address in range(0, len(data), 16):
        chunk = data[address:address+16]
        row = bytes([len(chunk), address >> 8, address & 255, 0]) + chunk
        lines.append(':' + (row + bytes([-sum(row) & 255])).hex())
    return ('\n'.join(lines) + '\n:00000001FF\n').encode()


def ldi(value):
    return 0xe000 | ((value & 0xf0) << 4) | (value & 15)  # r16


def out(address):
    return 0xb800 | ((address & 0x30) << 5) | (16 << 4) | (address & 15)


@unittest.skipUnless(os.environ.get('RUN_CPU_TESTS') == '1', 'CPU inspector build required')
class BusTraceTests(unittest.TestCase):
    def run_program(self, words, cycles=10000, limit=1000, start=0):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'synthetic.hex'
            path.write_bytes(hex_program(words))
            plain = inspect.inspect(path, ROOT/'build/cpu_inspector', cycles)
            traced = inspect.inspect(path, ROOT/'build/cpu_inspector', cycles,
                                     trace_limit=limit, trace_start=start)
            trace = traced['simulation'].pop('busTrace')
            self.assertEqual(plain['simulation'], traced['simulation'])
            return trace

    def test_equal_writes_and_pin_toggle_preserve_device_callback(self):
        t = self.run_program([ldi(0x20),out(4),out(5),out(5),out(3),0xb113,0xcfff])
        writes = [e for e in t['events'] if e['kind']=='write' and e['address']==0x25]
        self.assertEqual([e['value'] for e in writes], [0x20,0x20])
        self.assertEqual([e['pc'] for e in writes], [4,6])
        toggle = next(e for e in t['events'] if e['kind']=='write' and e['address']==0x23)
        self.assertEqual(toggle['port'][0], 0)
        read = next(e for e in t['events'] if e['kind']=='read' and e['address']==0x23)
        self.assertEqual(read['value'] & 0x20, 0)

    def test_spi_equal_bytes_and_fixed_delay(self):
        words = [ldi(0x50),out(0x2c),ldi(0xa5),out(0x2e)] + [0]*2000
        words += [out(0x2e)] + [0]*2000 + [0xcfff]
        t = self.run_program(words)
        writes = [e for e in t['events'] if e['kind']=='write' and e['address']==0x4e]
        outputs = [e for e in t['events'] if e['kind']=='spi_output']
        self.assertEqual([e['value'] for e in outputs], [0xa5,0xa5])
        self.assertEqual(t['spiOutputs'], 2)
        self.assertTrue(all(1600 <= b['cycle']-a['cycle'] <= 1601 for a,b in zip(writes,outputs)))

    def test_bounded_capture_does_not_stop_cpu(self):
        words = [ldi(0x20),out(5),out(5),out(5),0xcfff]
        t = self.run_program(words, limit=1)
        self.assertEqual(t['stored'], 1)
        self.assertEqual(t['dropped'], 2)
        self.assertTrue(t['truncated'])
        t = self.run_program(words, limit=10, start=3)
        self.assertEqual(t['beforeWindow'], 2)
        self.assertEqual(t['events'][0]['cycle'], 3)

    def test_trace_argument_guards(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.hex';path.write_bytes(hex_program([0xcfff]))
            for limit,start in [(0,0),(100001,0),(True,0),(1,-1),(1,10000),(1,True)]:
                with self.assertRaises(ValueError):
                    inspect.inspect(path,ROOT/'build/cpu_inspector',10000,trace_limit=limit,trace_start=start)
            with self.assertRaises(ValueError):
                inspect.inspect(path,trace_limit=1)


class DecoderTests(unittest.TestCase):
    def waveform(self, values, released_from=None, tail=0):
        events=[];port=[0,0,64];ddr=[40,0,64]
        def emit():
            events.append({'cycle':len(events)*4,'pc':0,'port':port[:],'ddr':ddr[:],
                           'spcr':0,'kind':'write','address':0x25,'value':port[0]})
        emit();port[2]=0;emit()
        for n,byte in enumerate(values):
            if n==released_from: ddr[0]&=~8
            for bit in range(8):
                port[0]&=~32;emit()
                port[0]=(port[0]&~8)|(((byte>>bit)&1)<<3);emit()
                port[0]|=32;emit()
        for _ in range(tail):
            port[0]&=~32;emit();port[0]|=32;emit()
        port[2]=64;emit()
        return events

    def frames(self,events):
        return analysis.gpio_frames(events,'PD6','PB5','PB3')

    def test_lsb_order_and_strobe_boundary(self):
        frames=self.frames(self.waveform([0x28,0xa5,0x3c]))
        self.assertEqual(len(frames),1)
        self.assertEqual(frames[0]['bytes'],[0x28,0xa5,0x3c])
        self.assertFalse(frames[0]['partialStart'])
        self.assertFalse(frames[0]['partialEnd'])

    def test_input_bits_are_unknown(self):
        f=self.frames(self.waveform([0x49,0xff,0xff],released_from=1))[0]
        self.assertEqual(f['bytes'],[0x49,None,None])
        self.assertEqual(f['releasedBits'],16)
        self.assertEqual(analysis.StledWriteShadow().apply(f),'read_request_only')

    def test_partial_boundaries_and_tail(self):
        events=self.waveform([0x00,0xa5],tail=3)
        f=self.frames(events)[0]
        self.assertEqual(f['trailingBits'],3)
        shadow=analysis.StledWriteShadow();shadow.apply(f)
        self.assertEqual(shadow.pages[0][0],0xa5)
        partial=self.frames(events[4:-1])[0]
        self.assertTrue(partial['partialStart']);self.assertTrue(partial['partialEnd'])
        self.assertEqual(shadow.apply(partial),'uninterpreted')

    def test_spi_enabled_or_undriven_clock_is_not_gpio_data(self):
        for variant in ('spi','input'):
            events=self.waveform([0x0d])
            for e in events:
                if variant=='spi':e['spcr']=0x50
                else:e['ddr'][0]&=~32
            f=self.frames(events)[0]
            self.assertEqual(f['bytes'],[None])
            self.assertEqual(f['unsupportedEdges'],8)

    def test_shadow_auto_fixed_and_display_control(self):
        shadow=analysis.StledWriteShadow()
        for values in ([0x00,1,2,3],[0x21,9,8],[0x2d]):
            shadow.apply(self.frames(self.waveform(values))[0])
        self.assertEqual(shadow.pages[0],[1,8,3,None,None,None])
        self.assertTrue(shadow.display_on)
        shadow.apply(self.frames(self.waveform([0x0e]))[0]);self.assertFalse(shadow.display_on)
        f=self.frames(self.waveform([0x05,7,8]))[0]
        self.assertEqual(shadow.apply(f),'unsupported_payload_or_address')
        self.assertEqual(shadow.pages[0][5],7)

    def test_spi_candidate_partial_and_complete_groups(self):
        events=self.waveform([0x00])
        for e in events[3:5]:e['kind']='spi_output';e['value']=0xa5
        groups=analysis.spi_groups(events,'PD6')
        self.assertEqual(groups[0]['bytes'],[0xa5,0xa5])
        self.assertFalse(groups[0]['partialStart'])
        self.assertFalse(groups[0]['partialEnd'])
        self.assertTrue(analysis.spi_groups(events[3:-1],'PD6')[0]['partialStart'])

    def test_empty_and_invalid_signals(self):
        self.assertEqual(self.frames([]),[])
        for pin in ('PE0','PB8','PB00','PB-1'):
            with self.assertRaises(ValueError):analysis.signal(pin)
        with self.assertRaises(ValueError):analysis.gpio_frames([],'PB0','PB0','PB1')


if __name__=='__main__': unittest.main()
