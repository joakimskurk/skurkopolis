#!/usr/bin/env python3
"""Pinned-image, synthetic-response experiments; requires the local original HEX."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'host'))
from inspect_firmware import inspect


def raw_report(report):
    return (json.dumps(report,indent=2)+'\n').encode()


def key_reads(events,window=False):
    samples=[e for e in events if e['kind']=='read' and e['address']==0x23 and e['pc'] in (0x7ac,0x7e6)]
    leading=0
    if window:
        pattern=[0x7ac]*8+[0x7e6]*8
        while leading<min(16,len(samples)) and [e["pc"] for e in samples[leading:leading+16]]!=pattern:
            leading+=1
        samples=samples[leading:]
    result=Counter()
    for i in range(0,len(samples)-15,16):
        batch=samples[i:i+16]
        if [e['pc'] for e in batch]!=[0x7ac]*8+[0x7e6]*8:
            raise AssertionError('Unexpected original key-read layout')
        result[sum(((e['value']>>3)&1)<<j for j,e in enumerate(batch))]+=1
    return dict(result),len(samples)%16,leading


def spi_words(events,first,second,window=False):
    high=None;words=Counter();leading=False
    for e in events:
        if e['kind']!='read' or e['address']!=0x4e:continue
        if e['pc']==first:
            if high is not None:raise AssertionError('Missing second SPI byte')
            high=e['value']
        elif e['pc']==second:
            if high is None:
                if window and not words and not leading:
                    leading=True;continue
                raise AssertionError('Missing first SPI byte')
            words[(high<<8)|e['value']]+=1;high=None
    return dict(words),high is not None,leading


def main(timing=None):
    firmware=ROOT/'firmware-local/metropolis_1.37.hex';runner=ROOT/'build/cpu_inspector'
    provenance=json.loads((ROOT/'artifacts/original-firmware-provenance.json').read_text())
    if hashlib.sha256(firmware.read_bytes()).hexdigest()!=provenance['hexSha256']:
        raise ValueError('Expected pinned original 1.37 HEX')
    old=json.loads((ROOT/'artifacts/original-bus-startup.json').read_text())
    unwired=inspect(firmware,runner,20000000,trace_limit=100000)
    unwired_sha=hashlib.sha256(raw_report(unwired)).hexdigest()
    if unwired_sha!=old['traceSha256']:
        raise AssertionError('Unwired baseline differs from v0.6 startup trace')
    print('Unwired v0.6 startup trace preserved',flush=True)
    folder=ROOT/('firmware-local/timing-analysis' if timing else 'firmware-local/response-analysis');folder.mkdir(exist_ok=True)
    experiments=[]
    cycles=23500000 if timing else 30000000
    trace_start=23000000 if timing else 0
    for name in ('neutral','channel-ramp','key-pulse','channel-ramp-key-pulse'):
        fixture=ROOT/'specs/fixtures'/(name+'.json')
        a=inspect(firmware,runner,cycles,trace_limit=100000,trace_start=trace_start,fixture=fixture,spi_timing=timing)
        b=inspect(firmware,runner,cycles,trace_limit=100000,trace_start=trace_start,fixture=fixture,spi_timing=timing)
        plain=inspect(firmware,runner,cycles,fixture=fixture,spi_timing=timing)
        sim=a['simulation'];trace=sim['busTrace'];f=sim['responseFixture']
        if a!=b or {k:v for k,v in sim.items() if k!='busTrace'}!=plain['simulation']:
            raise AssertionError('Repeatability or observer parity failed')
        if not a['runCompletedToLimit'] or trace['truncated']:
            raise AssertionError('Incomplete experiment or truncated trace')
        if f['spiFaults'] or f['stled']['directionFaults'] or f['stled']['unsupported']:
            raise AssertionError('Unexpected fixture protocol fault')
        if timing and (sim['spiTiming']['busyWrites'] or sim['spiTiming']['nonMasterWrites']):
            raise AssertionError('Unsupported SPI timing use')
        if any(scan['malformed'] for scan in f['scans']):raise AssertionError('Malformed SPI request')
        keys,tail,leading=key_reads(trace['events'],bool(timing))
        if not a['fixture']['keyEvents'] and (set(keys)!={0} or (not timing and keys!={0:f['stled']['keyComplete']})):
            raise AssertionError('Unexpected neutral key input')
        if a['fixture']['keyEvents'] and not keys.get(1,0):raise AssertionError('Key event not read by CPU')
        scans={}
        for pin,lo,hi in [('PC5',0x3fc,0x406),('PC4',0x467a,0x4684)]:
            words,partial,partial_start=spi_words(trace['events'],lo,hi,bool(timing))
            if set(words)!=set(a['fixture']['spiWords'][pin]):
                raise AssertionError('CPU did not read the expected channel words')
            scans[pin]={'wordCounts':words,'partialWordAtStop':partial,'partialWordAtStart':partial_start}
        raw=raw_report(a);(folder/(name+'.json')).write_bytes(raw)
        experiments.append({'name':name,'fixture':a['fixture'],'fixtureSha256':a['fixtureSha256'],
                            'cycleLimit':cycles,'traceStart':trace_start,
                            **({'spiTiming':sim['spiTiming']} if timing else {}),'stopReason':sim['stopReason'],'finalPc':sim['finalPc'],
                            'repeatIdentical':True,'tracedAndUntracedReportIdentical':True,
                            'traceSha256':hashlib.sha256(raw).hexdigest(),'retainedEvents':trace['stored'],
                            'keyReadWordCounts':keys,'partialKeyBitsAtStop':tail,'partialKeyBitsAtStart':leading,'cpuSpiReads':scans,
                            'responseFixture':f})
        print(name+': repeatability, CPU reads, no protocol faults and observer parity passed',flush=True)
    report={'schema':1,'version':'0.8.0' if timing else '0.7.0','date':'2026-10-22' if timing else '2026-10-20','input':unwired['input'],
            'boardEmulated':False,'physicalMapChanged':False,'unwiredV06TracePreserved':True,
            'unwiredTraceSha256':unwired_sha,'experiments':experiments,
            'limits':['No physical net, ADC identity/packing or panel/key label is verified.',
                      'Sampled PINB3 key input and SPI byte response adapters; no electrical or IRQ simulation.',
                      ('SPI divider timing is an opt-in byte model; native simavr flags and collision limitations remain.' if timing else 'SPI fixed100us timing, default fuses and all-FF EEPROM are retained synthetic conditions.'),
                      'Changed display RAM proves changed firmware output under stimuli, not successful module boot or musical parity.']}
    (ROOT/('artifacts/spi-timing-verification.json' if timing else 'artifacts/response-fixture-verification.json')).write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spi-timing',choices=['avr-divider-v1'])
    main(parser.parse_args().spi_timing)
