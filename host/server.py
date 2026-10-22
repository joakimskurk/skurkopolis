#!/usr/bin/env python3
"""Local deterministic trace bridge, not a realtime or simavr server."""
import argparse
import json
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
ROOT=Path(__file__).resolve().parents[1]
def integer(x, lo, hi):
    if type(x) is not int or not lo <= x <= hi: raise ValueError('Integer outside supported range')
    return x

def validated_values(config):
    if not isinstance(config,dict) or set(config)!={'segments','stages'}: raise ValueError('Expected segments and stages')
    segments,stages=config['segments'],config['stages']
    if not isinstance(segments,list) or not 1<=len(segments)<=8: raise ValueError('Use 1 to 8 segments')
    if not isinstance(stages,list) or len(stages)!=8: raise ValueError('Exactly 8 stages required')
    values=[len(segments)]
    for s in segments:
        if not isinstance(s,list) or len(s)!=3: raise ValueError('Segment requires start, end, repeats')
        values.extend([integer(s[0],1,8)-1,integer(s[1],1,8)-1,integer(s[2],1,8)])
    for s in stages:
        if not isinstance(s,dict) or set(s)!={'note','pulses','ratchet','skip','rest'}: raise ValueError('Invalid stage fields')
        values.extend([integer(s['note'],0,127),integer(s['pulses'],1,8),integer(s['ratchet'],1,4),integer(s['skip'],0,1),integer(s['rest'],0,1)])
    return values

def trace(config,engine='native'):
    values=validated_values(config)
    if engine=='native':
        command=[str(ROOT/'build/metro_trace')]
        payload=' '.join(map(str,values)).encode()
    elif engine=='avr':
        count=values[0]
        # Fixed wire layout: count, 8 segment triples, 8 stage quintuples.
        payload=bytes(values[:1+3*count]+[0]*(24-3*count)+values[1+3*count:])
        command=[str(ROOT/'build/sim_runner'),str(ROOT/'build/avr/sim-probe.elf')]
    else: raise ValueError('Unknown engine')
    result=subprocess.run(command,input=payload,capture_output=True,timeout=5)
    if result.returncode:
        if engine=='avr' and b'firmware rejected configuration' not in result.stderr:
            raise RuntimeError('AVR simulation failed; no native fallback was used')
        raise ValueError('Engine rejected configuration')
    return json.loads(result.stdout)

class Handler(BaseHTTPRequestHandler):
    def send(self,status,data,mime='application/json'):
        if isinstance(data,dict): data=json.dumps(data).encode()
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path=='/api/health': return self.send(200,{'engine':'native-cpp','version':'0.9.0','hardware':False,'avrBuilt':(ROOT/'build/sim_runner').is_file() and (ROOT/'build/avr/sim-probe.elf').is_file()})
        files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
        if self.path not in files:return self.send(404,{'error':'Not found'})
        name,mime=files[self.path];self.send(200,(ROOT/'web'/name).read_bytes(),mime)
    def do_POST(self):
        if self.path not in ('/api/trace','/api/trace/avr'): return self.send(404,{'error':'Not found'})
        # No cross-origin access. Browser fetch must use JSON, not HTML form requests.
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(415,{'error':'JSON required'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=8192:raise ValueError('Invalid request size')
            self.connection.settimeout(3)
            payload=json.loads(self.rfile.read(length))
            self.send(200,trace(payload,'avr' if self.path.endswith('/avr') else 'native'))
        except (ValueError,TypeError):self.send(400,{'error':'Invalid configuration. Segments must cover stages 1 to 8 consecutively; repeats 1 to 8.'})
        except (OSError,subprocess.SubprocessError,RuntimeError):self.send(503,{'error':'Selected engine unavailable or failed. Build native tests and, for AVR, run sh scripts/build-sim.sh.'})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bind',default='127.0.0.1');parser.add_argument('--port',type=int,default=8080);args=parser.parse_args()
    print(f'Metropolis Lab http://{args.bind}:{args.port}',flush=True)
    HTTPServer((args.bind,args.port),Handler).serve_forever()
