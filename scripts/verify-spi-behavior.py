#!/usr/bin/env python3
"""Factorial timing/status comparison and one-input sweeps using local original HEX."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'host'))
from inspect_firmware import inspect
from experiment_analysis import summarize_window

PROFILES={
    'native-fixed':dict(spi_timing=None,spi_status=None),
    'native-divider':dict(spi_timing='avr-divider-v1',spi_status=None),
    'master-fixed':dict(spi_timing=None,spi_status='avr-master-v1'),
    'master-divider':dict(spi_timing='avr-divider-v1',spi_status='avr-master-v1')
}
STOPS=(23500000,30000000)


def configurations(suite):
    neutral=json.loads((ROOT/'specs/fixtures/neutral.json').read_text())
    if suite=='matrix':
        return [(name,json.loads((ROOT/'specs/fixtures'/f'{name}.json').read_text()))
                for name in ('neutral','channel-ramp','key-pulse','channel-ramp-key-pulse')]
    result=[('neutral',neutral)]
    for bit in range(16):
        c=copy.deepcopy(neutral);value=1<<bit
        c['keyEvents']=[{'cycle':22000000,'bytes':[value&255,value>>8]},
                        {'cycle':24000000,'bytes':[0,0]}]
        result.append((f'key-bit-{bit:02}',c))
    for pin in ('PC5','PC4'):
        for channel in range(8):
            c=copy.deepcopy(neutral);c['spiWords'][pin][channel]=512
            result.append((f'{pin}-channel-{channel}',c))
    return result


def verify_case(firmware,private,name,config,profile,stop):
    stem=f'{name}_{profile}_{stop}'
    fixture=private/(name+'.json');fixture.write_text(json.dumps(config,indent=2)+'\n')
    kwargs=dict(fixture=fixture,**PROFILES[profile])
    a=inspect(firmware,ROOT/'build/cpu_inspector',stop,trace_limit=100000,trace_start=stop-500000,**kwargs)
    b=inspect(firmware,ROOT/'build/cpu_inspector',stop,trace_limit=100000,trace_start=stop-500000,**kwargs)
    plain=inspect(firmware,ROOT/'build/cpu_inspector',stop,**kwargs)
    s=a['simulation'];trace=s['busTrace'];f=s['responseFixture']
    if a!=b or {k:v for k,v in s.items() if k!='busTrace'}!=plain['simulation']:
        raise AssertionError('Repeatability/observer parity: '+stem)
    if not a['runCompletedToLimit'] or trace['truncated']:
        raise AssertionError('Incomplete run/window: '+stem)
    if f['spiFaults'] or f['stled']['unsupported'] or f['stled']['directionFaults'] or any(x['malformed'] for x in f['scans']):
        raise AssertionError('Protocol fault: '+stem)
    if any(not all(x['channelReads']) for x in f['scans']):
        raise AssertionError('Not all eight channels requested: '+stem)
    master=s.get('spiMaster')
    if master and any(master[k] for k in ('collisions','ignoredNonMasterWrites','abortedTransfers')):
        raise AssertionError('Unexpected master fault: '+stem)
    obs=summarize_window(trace['events'])
    expected_key=0
    for e in config['keyEvents']:
        if e['cycle']<=stop-500000:expected_key=e['bytes'][0]|e['bytes'][1]<<8
    if set(obs['completeKeyWords'])!={expected_key}:
        raise AssertionError('Expected CPU key value not observed: '+stem)
    for pin,values in config['spiWords'].items():
        if set(obs['cpuSpiReads'][pin]['wordCounts'])!=set(values):
            raise AssertionError('Expected CPU channel words not observed: '+stem)
    raw=(json.dumps(a,indent=2)+'\n').encode();(private/(stem+'-trace.json')).write_bytes(raw)
    result={'name':name,'profile':profile,'cycleLimit':stop,'traceStart':stop-500000,
            'fixtureSha256':a['fixtureSha256'],'rawTraceSha256':hashlib.sha256(raw).hexdigest(),
            'repeatIdentical':True,'untracedReportIdentical':True,'events':trace['stored'],
            'finalPc':s['finalPc'],'spiMaster':master,
            'finalPages':f['stled']['pages'],'displayOn':f['stled']['displayOn'],
            'keyReadsWholeRun':f['stled']['keyComplete'],'spiResponsesWholeRun':f['spiResponses'],
            'channelReadsWholeRun':{x['select']:x['channelReads'] for x in f['scans']},
            'observations':obs}
    print(stem+': passed',flush=True)
    return result


def comparisons(experiments):
    results=[]
    index={(x['name'],x['profile'],x['cycleLimit']):x for x in experiments}
    for x in experiments:
        base=index[('neutral',x['profile'],x['cycleLimit'])]
        if x['name']=='neutral':continue
        patterns=lambda e:sorted(p['bytes'] for p in e['observations']['displayPayloads'])
        results.append({'name':x['name'],'profile':x['profile'],'cycleLimit':x['cycleLimit'],
                        'finalPagesChanged':x['finalPages']!=base['finalPages'],
                        'displayPayloadSetChanged':patterns(x)!=patterns(base),
                        'writeSequenceChanged':x['observations']['writeSequenceSha256']!=base['observations']['writeSequenceSha256']})
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=['matrix','sweep'],default='matrix')
    args=parser.parse_args()
    firmware=ROOT/'firmware-local/metropolis_1.37.hex'
    pin=json.loads((ROOT/'artifacts/original-firmware-provenance.json').read_text())['hexSha256']
    if hashlib.sha256(firmware.read_bytes()).hexdigest()!=pin:raise ValueError('Wrong firmware hash')
    baseline=inspect(firmware,ROOT/'build/cpu_inspector',20000000,trace_limit=100000)
    baseline_sha=hashlib.sha256((json.dumps(baseline,indent=2)+'\n').encode()).hexdigest()
    expected=json.loads((ROOT/'artifacts/original-bus-startup.json').read_text())['traceSha256']
    if baseline_sha!=expected:raise AssertionError('Unwired baseline changed')
    private=ROOT/'firmware-local/behavior-analysis'/args.suite;private.mkdir(parents=True,exist_ok=True)
    cases=configurations(args.suite);experiments=[]
    profiles=PROFILES if args.suite=='matrix' else ['master-divider']
    for name,config in cases:
        for profile in profiles:
            for stop in STOPS:
                experiments.append(verify_case(firmware,private,name,config,profile,stop))
    report={'schema':1,'version':'0.9.0','suite':args.suite,'date':'2026-10-22',
            'inputSha256':pin,'unwiredTraceSha256':baseline_sha,'boardEmulated':False,'physicalMapChanged':False,
            'configurations':dict(cases),'profiles':{k:PROFILES[k] for k in profiles},
            'experiments':experiments,'relativeToNeutral':comparisons(experiments),
            'limits':['Raw key bits and synthetic 16-bit channel words have no verified panel labels.',
                      'Identical time bounds isolate software profile effects, not physical accuracy.',
                      'Different write-sequence hashes can reflect scan rate/count rather than different values.',
                      'No analog CV, gate, successful board boot or musical parity is established.']}
    if args.suite=='matrix':
        idx={(x['name'],x['profile'],x['cycleLimit']):x for x in experiments}
        archived=json.loads((ROOT/'artifacts/spi-timing-verification.json').read_text())
        for old in archived['experiments']:
            if idx[old['name'],'native-divider',23500000]['rawTraceSha256']!=old['traceSha256']:
                raise AssertionError('Archived v0.8 trace changed: '+old['name'])
        report['archivedV08TracesPreserved']=True
        report['profileComparisons']=[]
        for name,_ in cases:
            for stop in STOPS:
                for left,right in [('native-fixed','native-divider'),('master-fixed','master-divider'),
                                   ('native-fixed','master-fixed'),('native-divider','master-divider')]:
                    a,b=idx[name,left,stop],idx[name,right,stop]
                    report['profileComparisons'].append({'name':name,'cycleLimit':stop,'left':left,'right':right,
                        'finalPagesEqual':a['finalPages']==b['finalPages'],
                        'cpuSpiWordSetsEqual':all(set(a['observations']['cpuSpiReads'][p]['wordCounts'])==set(b['observations']['cpuSpiReads'][p]['wordCounts']) for p in ('PC5','PC4')),
                        'wholeRunResponseCounts':[a['spiResponsesWholeRun'],b['spiResponsesWholeRun']]})
    dest=ROOT/'artifacts'/f'spi-behavior-{args.suite}.json'
    dest.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(f'Saved {len(experiments)} verified cases ({len(experiments)*3} runs)',flush=True)


if __name__=='__main__':main()
