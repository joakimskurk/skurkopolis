import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_bus_trace import hex_program, ldi, out, module, ROOT

inspector=module('inspect_firmware')
config_module=module('fixture_config')


def profile():
    return {'schema':1,'profile':'rev010-hypothesis-v1','keyBytes':[0xa5,0x5a],
            'spiWords':{'PC5':[0x1234,0xabcd,0x5678,0,0,0,0,0],
                        'PC4':[0x1122,0x3344,0x5566,0,0,0,0,0]},'keyEvents':[]}


def bitop(address,bit,high):
    return (0x9a00 if high else 0x9800)|(address<<3)|bit


def read(address,register=17):
    return 0xb000|((address&0x30)<<5)|(register<<4)|(address&15)


def key_program(release=True,command=0x49):
    words=[ldi(64),out(0x0a),bitop(0x0b,6,True),ldi(40),out(4),bitop(0x0b,6,False)]
    for bit in range(8):
        words += [bitop(5,5,False),bitop(5,3,(command>>bit)&1),bitop(5,5,True)]
    if release:words += [bitop(4,3,False)]
    for _ in range(16):
        words += [bitop(5,5,False),read(3),bitop(5,5,True)]
    words += [bitop(4,3,True),bitop(0x0b,6,True),0xcfff]
    return words


def spi_setup():
    return [ldi(4),out(4),out(5),ldi(0x30),out(7),out(8),ldi(0x50),out(0x2c)]


def transfer(value):
    return [ldi(value),out(0x2e),read(0x2d),0xff17,0xcffd,read(0x2e,18)]


class ConfigTests(unittest.TestCase):
    def test_schema_and_binary_length(self):
        c=profile();data=config_module.encode(c)
        self.assertEqual(data[:8],b'SKFX0001');self.assertEqual(len(data),43)
        c['keyEvents']=[{'cycle':0,'bytes':[1,2]},{'cycle':100,'bytes':[3,4]}]
        self.assertEqual(len(config_module.encode(c)),63)

    def test_bounds_types_unknown_fields(self):
        bad=[]
        for field,value in [('schema',True),('profile','physical'),('keyBytes',[256,0]),
                            ('keyBytes',[False,0]),('spiWords',{'PC5':[0]*8}),('keyEvents',None)]:
            c=profile();c[field]=value;bad.append(c)
        c=profile();c['spiWords']['PC5'][0]=65536;bad.append(c)
        c=profile();c['verified']=True;bad.append(c)
        for events in ([{'cycle':-1,'bytes':[0,0]}], [{'cycle':5,'bytes':[0,0]}]*2,
                       [{'cycle':True,'bytes':[0,0]}], [{'cycle':100000001,'bytes':[0,0]}],
                       [{'cycle':i,'bytes':[0,0]} for i in range(33)]):
            c=profile();c['keyEvents']=events;bad.append(c)
        for c in bad:
            with self.assertRaises(ValueError):config_module.encode(c)

    def test_duplicate_json_fields_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'config.json';p.write_text('{"schema":1,"schema":1}')
            with self.assertRaises(ValueError):config_module.load(p)


@unittest.skipUnless(os.environ.get('RUN_CPU_TESTS')=='1','CPU inspector build required')
class FixtureIntegrationTests(unittest.TestCase):
    def run_fixture(self,words,config=None,cycles=20000,trace=True):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.hex';p.write_bytes(hex_program(words))
            f=Path(folder)/'fixture.json';f.write_text(json.dumps(profile() if config is None else config))
            return inspector.inspect(p,ROOT/'build/cpu_inspector',cycles,
                                     trace_limit=10000 if trace else None,fixture=f)['simulation']

    def test_key_bits_reach_cpu_and_trace_is_passive(self):
        words=key_program();s=self.run_fixture(words)
        events=s.pop('busTrace')['events']
        self.assertEqual(s,self.run_fixture(words,trace=False))
        bits=[(e['value']>>3)&1 for e in events if e['kind']=='read' and e['address']==0x23]
        self.assertEqual(sum(x<<i for i,x in enumerate(bits)),0x5aa5)
        state=s['responseFixture']['stled']
        self.assertEqual(state['keyComplete'],1);self.assertEqual(state['pinReadOverrides'],16)
        self.assertEqual(state['directionFaults'],0)
        self.assertEqual(s['scope'],'synthetic_response_hypothesis')

    def test_wrong_direction_and_unsupported_command_do_not_drive(self):
        s=self.run_fixture(key_program(release=False))['responseFixture']['stled']
        self.assertEqual(s['pinReadOverrides'],0);self.assertEqual(s['directionFaults'],1)
        s=self.run_fixture(key_program(command=0x48))['responseFixture']['stled']
        self.assertEqual(s['pinReadOverrides'],0);self.assertEqual(s['unsupported'],1)

    def test_spi_two_devices_channel_words_and_identical_bytes(self):
        words=spi_setup()
        for cs in (5,4):
            for command in (0,8):
                words += [bitop(8,cs,False)]+transfer(command)+transfer(0)+[bitop(8,cs,True)]
        words += [0xcfff]
        c=profile();c['spiWords']['PC4'][1]=0x4444
        s=self.run_fixture(words,c);events=s.pop('busTrace')['events']
        self.assertEqual(s,self.run_fixture(words,c,trace=False))
        rx=[e['value'] for e in events if e['kind']=='read' and e['address']==0x4e]
        self.assertEqual(rx,[0x12,0x34,0xab,0xcd,0x11,0x22,0x44,0x44])
        f=s['responseFixture'];self.assertEqual(f['spiResponses'],8);self.assertEqual(f['spiFaults'],0)
        self.assertEqual([x['complete'] for x in f['scans']],[2,2])

    def test_cs_overlap_aborts_response(self):
        words=spi_setup()+[bitop(8,5,False),bitop(8,4,False)]+transfer(0)+transfer(0)+[0xcfff]
        f=self.run_fixture(words)['responseFixture']
        self.assertEqual(f['spiResponses'],0);self.assertEqual(f['spiFaults'],2)

    def test_cs_change_during_pending_byte_is_rejected(self):
        words=spi_setup()+[bitop(8,5,False),ldi(0),out(0x2e),bitop(8,5,True)]
        words += [0]*1800+[0xcfff]
        f=self.run_fixture(words)['responseFixture']
        self.assertEqual(f['spiResponses'],0);self.assertEqual(f['spiFaults'],1)

    def test_key_events_apply_at_boundaries_and_latch_at_command(self):
        c=profile();c['keyEvents']=[{'cycle':0,'bytes':[0x11,0x22]},
                                   {'cycle':1000,'bytes':[0x33,0x44]},
                                   {'cycle':30000,'bytes':[0x55,0x66]}]
        s=self.run_fixture(key_program(),c);f=s['responseFixture']
        bits=[(e['value']>>3)&1 for e in s['busTrace']['events'] if e['kind']=='read' and e['address']==0x23]
        self.assertEqual(sum(x<<i for i,x in enumerate(bits)),0x2211)
        self.assertEqual(f['eventsApplied'],2);self.assertEqual(f['stled']['keyBytes'],[0x33,0x44])
        self.assertFalse(f['keyEvents'][2]['applied'])

    def test_invalid_binary_fixture_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'flash.bin';binary.write_bytes(b'\xff\xcf'+b'\xff'*32766)
            fixture=Path(folder)/'fixture.bin';valid=config_module.encode(profile())
            for contents in (b'',valid[:-1],valid+b'x',b'BROKEN!!'+valid[8:]):
                fixture.write_bytes(contents)
                p=subprocess.run([str(ROOT/'build/cpu_inspector'),str(binary),'1000','16000000',str(fixture)],capture_output=True)
                self.assertEqual(p.returncode,1)


if __name__=='__main__':unittest.main()
