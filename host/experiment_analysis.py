"""Window-scoped observations; no physical panel or musical labels are inferred."""
from collections import Counter
import hashlib
import json
from analyze_bus import gpio_frames


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def word_reads(events,first,second):
    high=None;counts=Counter();leading=False;seen=False
    for e in events:
        if e['kind']!='read' or e['address']!=0x4e or e['pc'] not in (first,second):continue
        if e['pc']==first:
            if high is not None:raise ValueError('Missing SPI low byte inside window')
            high=e['value']
        elif high is None:
            if seen:raise ValueError('Missing SPI high byte inside window')
            leading=True
        else:
            counts[(high<<8)|e['value']]+=1;high=None
        seen=True
    return {'wordCounts':dict(counts),'partialAtStart':leading,'partialAtStop':high is not None}


def summarize_window(events):
    frames=gpio_frames(events,'PD6','PB5','PB3')
    complete=[f for f in frames if not f['partialStart'] and not f['partialEnd']]
    keys=Counter();writes=[];display=Counter()
    samples=[e for e in events if e['kind']=='read' and e['address']==0x23 and e['pc'] in (0x7ac,0x7e6)]
    cursor=0
    for f in complete:
        if f['unsupportedEdges'] or f['trailingBits']:
            raise ValueError('Malformed complete GPIO frame')
        data=f['bytes']
        if data and data[0]==0x49:
            while cursor<len(samples) and samples[cursor]['cycle']<f['startCycle']:cursor+=1
            batch=[]
            while cursor<len(samples) and samples[cursor]['cycle']<=f['endCycle']:
                batch.append(samples[cursor]);cursor+=1
            if [e['pc'] for e in batch]!=[0x7ac]*8+[0x7e6]*8:
                raise ValueError('Unexpected complete key-read frame')
            keys[sum(((e['value']>>3)&1)<<i for i,e in enumerate(batch))]+=1
        elif data and data[0] is not None and not data[0]&0x40:
            if any(x is None for x in data):raise ValueError('Released data in write frame')
            writes.append(data)
            if data[0]==0 and len(data)==7:display[tuple(data[1:])]+=1
    return {
        'completeKeyWords':dict(keys),
        'partialGpioFrames':sum(f['partialStart'] or f['partialEnd'] for f in frames),
        'displayPayloads':[{'bytes':list(k),'count':v} for k,v in sorted(display.items())],
        'completeWriteFrames':len(writes),'writeSequenceSha256':digest(writes),
        'writePatterns':[{'bytes':list(k),'count':v} for k,v in sorted(Counter(tuple(w) for w in writes).items())],
        'cpuSpiReads':{pin:word_reads(events,a,b) for pin,a,b in [('PC5',0x3fc,0x406),('PC4',0x467a,0x4684)]}
    }
