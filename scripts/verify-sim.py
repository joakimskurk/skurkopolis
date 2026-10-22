#!/usr/bin/env python3
"""Actual AVR ELF execution compared to native C++; no mock simulator."""
import importlib.util,json,random,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('server',root/'host/server.py');server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
def config():return {'segments':[[1,3,2],[4,5,2],[6,8,2]],'stages':[dict(note=n,pulses=1,ratchet=1,skip=0,rest=0) for n in [48,50,55,53,57,55,59,60]]}
fixtures=[config()];c=config();c['segments']=[[1,8,8]]
for s in c['stages']:s.update(pulses=8,ratchet=4)
fixtures.append(c)
c=config()
for s in c['stages']:s['skip']=1
fixtures.append(c)
# All 128 possible consecutive partitions; independent patterns, skips, rests.
rng=random.Random(328010)
for mask in range(128):
 c=config();start=1;c['segments']=[]
 for stage in range(1,9):
  if stage==8 or mask&(1<<(stage-1)):
   c['segments'].append([start,stage,rng.randint(1,8)]);start=stage+1
 for s in c['stages']:s.update(note=rng.randint(0,127),pulses=rng.randint(1,8),ratchet=rng.randint(1,4),skip=int(rng.random()<.25),rest=int(rng.random()<.25))
 fixtures.append(c)
max_cycles=max_stack=total=0;canonical=None
for index,c in enumerate(fixtures):
 native=server.trace(c);avr=server.trace(c,'avr')
 assert native['events']==avr['events'],f'Parity failure fixture {index}'
 m=avr['simulation'];assert m['sramCapacity']==2048 and m['flashCapacity']==32768
 assert m['staticSramBytes']+m['observedStackBytes']<2048
 max_cycles=max(max_cycles,m['maxRequestCycles']);max_stack=max(max_stack,m['observedStackBytes']);total+=len(avr['events'])
 if index==0:canonical=avr
# Fail on illegal segment topology in the AVR core, not just Python validation.
for seg in [[[1,3,2],[3,8,2]],[[1,3,2],[5,8,2]]]:
 c=config();c['segments']=seg
 try:server.trace(c,'avr')
 except ValueError:pass
 else:raise AssertionError('AVR accepted invalid partition')
report={'status':'PASS','fixtures':len(fixtures),'pulsesCompared':total,'maxInstrumentedRequestCycles':max_cycles,'maxObservedStackBytesAfterBoot':max_stack,'canonical':canonical,'elfSha256':hashlib.sha256((root/'build/avr/sim-probe.elf').read_bytes()).hexdigest(),'limitations':['No rev010 peripherals','Synthetic 16 MHz, real clock unknown','simavr 1.6 ATmega328 alias reports 328P signature','Cycles include mailbox and encoding; not gate timing','Observed stack after boot is not worst-case production stack']}
(root/'build/sim-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'PASS: {len(fixtures)} actual AVR runs, {total} pulses equal native; maximum request {max_cycles} cycles, observed stack {max_stack} bytes')
