#!/usr/bin/env python3
"""Reproduce the pinned original-firmware experiments locally; no hardware access."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'host'))
from inspect_firmware import inspect, parse_hex
from analyze_bus import summarize


def main():
    firmware=ROOT/'firmware-local/metropolis_1.37.hex'
    provenance=json.loads((ROOT/'artifacts/original-firmware-provenance.json').read_text())
    _,metadata=parse_hex(firmware.read_bytes())
    if metadata['hexSha256']!=provenance['hexSha256']:
        raise ValueError('Firmware differs from the pinned v1.37 experiment')
    private=ROOT/'firmware-local/analysis';private.mkdir(exist_ok=True)
    results=[]
    for label,cycles,start in [('startup',20000000,0),('late',80000000,78000000)]:
        baseline=inspect(firmware,ROOT/'build/cpu_inspector',cycles)
        first=inspect(firmware,ROOT/'build/cpu_inspector',cycles,trace_limit=100000,trace_start=start)
        repeat=inspect(firmware,ROOT/'build/cpu_inspector',cycles,trace_limit=100000,trace_start=start)
        state={k:v for k,v in first['simulation'].items() if k!='busTrace'}
        if first!=repeat or state!=baseline['simulation']:
            raise AssertionError('Repeatability or observed CPU-report parity failed')
        if not first['runCompletedToLimit'] or first['simulation']['busTrace']['truncated']:
            raise AssertionError('Experiment did not retain the complete selected window')
        raw=(json.dumps(first,indent=2)+'\n').encode()
        (private/(label+'-trace.json')).write_bytes(raw)
        analysis=summarize(first,'PD6','PB5','PB3',['PB2','PC5','PC4'])
        analysis['traceSha256']=hashlib.sha256(raw).hexdigest()
        (ROOT/'artifacts'/('original-bus-'+label+'.json')).write_text(json.dumps(analysis,indent=2)+'\n')
        results.append({'label':label,'cycleLimit':cycles,'traceStart':start,
                        'repeatIdentical':True,'untracedCpuReportIdentical':True,
                        'retainedEvents':len(first['simulation']['busTrace']['events']),
                        'spiOutputCallbacksWholeRun':first['simulation']['busTrace']['spiOutputs'],
                        'traceSha256':analysis['traceSha256']})
        print(label+': repeatability, CPU-report parity and trace coverage passed',flush=True)
    report={'schema':1,'version':'0.6.0','date':'2026-10-20','input':metadata,
            'experiments':results,'physicalMapChanged':False,'boardEmulated':False,
            'claims':['Original CPU callback traces reproduced for the stated synthetic fixture.',
                      'Sampled CPU reports match uninstrumented runs; this is not full simulator-state equivalence.',
                      'No successful module boot, physical wiring, panel mapping or timing parity is certified.']}
    (ROOT/'artifacts/original-bus-verification.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError,AssertionError) as exc:
        raise SystemExit(str(exc))
