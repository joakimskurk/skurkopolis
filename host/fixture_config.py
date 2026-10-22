"""Strict synthetic fixture schema, separate from physical-map evidence."""
import json
import struct
from pathlib import Path


def integer(value, maximum, label):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Invalid '+label)
    return value


def vector(value, length, maximum, label):
    if not isinstance(value,list) or len(value)!=length:
        raise ValueError('Invalid '+label+' length')
    return [integer(x,maximum,label) for x in value]


def encode(config):
    if not isinstance(config,dict) or set(config)!={'schema','profile','keyBytes','spiWords','keyEvents'}:
        raise ValueError('Unexpected fixture fields')
    if type(config['schema']) is not int or config['schema']!=1 or config['profile']!='rev010-hypothesis-v1':
        raise ValueError('Unsupported fixture schema/profile')
    keys=vector(config['keyBytes'],2,255,'key bytes')
    words=config['spiWords']
    if not isinstance(words,dict) or set(words)!={'PC5','PC4'}:
        raise ValueError('SPI words require PC5 and PC4')
    words=vector(words['PC5'],8,65535,'PC5 words')+vector(words['PC4'],8,65535,'PC4 words')
    events=config['keyEvents']
    if not isinstance(events,list) or len(events)>32:
        raise ValueError('At most 32 key events are supported')
    payload=struct.pack('<8s2B16HB',b'SKFX0001',*keys,*words,len(events))
    previous=-1
    for event in events:
        if not isinstance(event,dict) or set(event)!={'cycle','bytes'}:
            raise ValueError('Invalid key event fields')
        cycle=integer(event['cycle'],100000000,'key event cycle')
        if cycle<=previous:raise ValueError('Key events must be strictly ordered')
        previous=cycle
        payload+=struct.pack('<Q2B',cycle,*vector(event['bytes'],2,255,'event key bytes'))
    return payload


def load(path):
    path=Path(path)
    if path.stat().st_size>16384:raise ValueError('Fixture exceeds 16 KiB')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate fixture field: '+key)
            result[key]=value
        return result
    config=json.loads(path.read_text(),object_pairs_hook=unique)
    return config,encode(config)
