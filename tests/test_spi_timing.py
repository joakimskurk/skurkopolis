import json
import os
from pathlib import Path
import tempfile
import unittest
from test_bus_trace import hex_program, ldi, out, ROOT, inspect
from test_response_fixture import spi_setup, bitop, transfer, profile, read


@unittest.skipUnless(os.environ.get('RUN_CPU_TESTS') == '1', 'CPU inspector build required')
class SpiTimingTests(unittest.TestCase):
    def run_program(self, words, hz=16000000, fixture=False):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.hex';p.write_bytes(hex_program(words))
            f=Path(folder)/'fixture.json';f.write_text(json.dumps(profile()))
            kwargs={'hz':hz,'spi_timing':'avr-divider-v1','fixture':f if fixture else None}
            a=inspect.inspect(p,ROOT/'build/cpu_inspector',10000,trace_limit=10000,**kwargs)['simulation']
            b=inspect.inspect(p,ROOT/'build/cpu_inspector',10000,**kwargs)['simulation']
            trace=a.pop('busTrace');self.assertEqual(a,b)
            self.assertFalse(trace['truncated'])
            return a,trace['events']

    def test_all_dividers_and_two_cpu_frequencies(self):
        for hz in (8000000,16000000):
            for index,divider in enumerate((4,16,64,128,2,8,32,64)):
                with self.subTest(hz=hz,index=index):
                    words=[ldi(0x50|(index&3)),out(0x2c),ldi(index>>2),out(0x2d),ldi(0xa5),out(0x2e)]
                    s,events=self.run_program(words+[0]*1100+[out(0x2e)]+[0]*1100+[0xcfff],hz)
                    writes=[e for e in events if e['kind']=='write' and e['address']==0x4e]
                    done=[e for e in events if e['kind']=='spi_output']
                    self.assertEqual([e['value'] for e in done],[0xa5,0xa5])
                    self.assertEqual([b['cycle']-a['cycle'] for a,b in zip(writes,done)],[8*divider]*2)
                    self.assertEqual(s['spiTiming']['configurationCounts'][index],2)
                    self.assertEqual(s['spiTiming']['busyWrites'],0)

    def test_spif_polling_and_synthetic_responses(self):
        words=spi_setup()+[bitop(8,5,False)]+transfer(0)+transfer(0)+[bitop(8,5,True),0xcfff]
        s,events=self.run_program(words,fixture=True)
        reads=[e['value'] for e in events if e['kind']=='read' and e['address']==0x4e]
        self.assertEqual(reads,[0x12,0x34])
        self.assertEqual(s['responseFixture']['spiResponses'],2)
        self.assertEqual(s['responseFixture']['spiFaults'],0)
        self.assertEqual(s['responseFixture']['spiTiming'],'avr-divider-v1')
        self.assertLessEqual(s['spiTiming']['maxCallbackLatenessCycles'],2)

    def test_busy_write_is_counted_and_retains_native_restart(self):
        words=[ldi(0x50),out(0x2c),ldi(0x11),out(0x2e),ldi(0x22),out(0x2e)]+[0]*100+[0xcfff]
        s,events=self.run_program(words)
        self.assertEqual(s['spiTiming']['busyWrites'],1)
        self.assertEqual([e['value'] for e in events if e['kind']=='spi_output'],[0x22])

    def test_disable_before_completion_preserves_native_suppression(self):
        words=[ldi(0x50),out(0x2c),ldi(0x11),out(0x2e),ldi(0),out(0x2c)]+[0]*100+[0xcfff]
        s,events=self.run_program(words)
        self.assertEqual(s['spiTiming']['timerCallbacks'],1)
        self.assertEqual([e for e in events if e['kind']=='spi_output'],[])

    def test_divider_latched_at_write_and_instruction_lateness_bounded(self):
        words=[ldi(0x53),out(0x2c),ldi(0x11),out(0x2e),ldi(0x50),out(0x2c),0xcfff]
        s,events=self.run_program(words)
        start=next(e for e in events if e['kind']=='write' and e['address']==0x4e)
        done=next(e for e in events if e['kind']=='spi_output')
        self.assertTrue(1024<=done['cycle']-start['cycle']<=1025)
        self.assertLessEqual(s['spiTiming']['maxCallbackLatenessCycles'],1)

    def test_invalid_profile_and_missing_runner(self):
        with self.assertRaises(ValueError):inspect.inspect('unused',spi_timing='unknown')
        with self.assertRaises(ValueError):inspect.inspect('unused',spi_timing='avr-divider-v1')


if __name__=='__main__':unittest.main()
