"""Decode simulator observations under explicit wiring hypotheses, never board facts."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def signal(text):
    if not isinstance(text, str) or not re.fullmatch(r'P[BCD][0-7]', text):
        raise ValueError('Signal must be PB0..PD7')
    return ord(text[1]) - ord('B'), int(text[2])


def level(event, pin, field='port'):
    port, bit = signal(pin)
    return (event[field][port] >> bit) & 1


def gpio_frames(events, strobe, clock, data):
    """Active-low strobe, rising-edge sample, LSB first; released data stays unknown.

    Only GPIO latch edges with SPE clear and output-configured clock/strobe count.
    This is a configurable decoder hypothesis, not a binding to any physical board.
    The first snapshot seeds state; an already-active frame is marked partial.
    """
    if len({strobe, clock, data}) != 3:
        raise ValueError('Signals must be distinct')
    for pin in (strobe, clock, data):
        signal(pin)
    frames, current, previous = [], None, None

    def begin(e, partial):
        return {'startCycle': e['cycle'], 'startPc': e['pc'], 'partialStart': partial,
                'bytes': [], 'bits': [], 'unsupportedEdges': 0}

    def finish(e, partial):
        current['endCycle'] = e['cycle']
        current['partialEnd'] = partial
        bits = current.pop('bits')
        current['bitCount'] = len(bits)
        current['trailingBits'] = len(bits) % 8
        current['releasedBits'] = sum(x is None for x in bits)
        current['bytes'] = [None if None in bits[i:i+8] else
                            sum(b << j for j, b in enumerate(bits[i:i+8]))
                            for i in range(0, len(bits)-7, 8)]
        frames.append(current)

    for e in events:
        if previous is None:
            if not level(e, strobe):
                current = begin(e, True)
            previous = e
            continue
        was, now = level(previous, strobe), level(e, strobe)
        if was and not now:
            current = begin(e, False)
        elif not was and now and current is not None:
            finish(e, False)
            current = None
        if current is not None and not now and not level(previous, clock) and level(e, clock):
            supported = (not e['spcr'] & 0x40 and level(e, clock, 'ddr') and
                         level(e, strobe, 'ddr'))
            if not supported:
                current['unsupportedEdges'] += 1
            current['bits'].append(level(e, data) if supported and level(e, data, 'ddr') else None)
        previous = e
    if current is not None:
        finish(previous, True)
    return frames


class StledWriteShadow:
    """Datasheet-based write subset. No keyscan, read responses, IRQ or analog model.

    Unknown reset contents deliberately remain None in a trace-derived shadow.
    Already-completed bytes survive a partial final byte. Out-of-range addressing
    stops interpretation; no undocumented wrap rule is invented.
    """
    def __init__(self):
        self.pages = [[None]*6, [None], [None]*4, [None]*4]
        self.display_on = None

    def apply(self, frame):
        values = frame['bytes']
        if frame['partialStart'] or frame['unsupportedEdges'] or not values or values[0] is None:
            return 'uninterpreted'
        command = values[0]
        if command & 0x40:
            return 'read_request_only'
        if command & 0x5f in (0x0d, 0x0e):
            self.display_on = (command & 0x5f) == 0x0d
            return 'display_control'
        page, address = (command >> 3) & 3, command & 7
        for value in values[1:]:
            if value is None or address >= len(self.pages[page]):
                return 'unsupported_payload_or_address'
            self.pages[page][address] = value
            if not command & 0x20:
                address += 1
        return 'write'


def spi_groups(events, select):
    """Group simulator SPI output-byte notifications under one candidate active-low CS.

    These are byte notifications, never reconstructed SPI wire edges. Multiple low
    candidate selects may produce overlapping hypotheses; no device identity follows.
    """
    signal(select)
    groups, current, previous = [], None, None
    for e in events:
        active = not level(e, select)
        if active and (previous is None or level(previous, select)):
            current = {'startCycle': e['cycle'], 'partialStart': previous is None,
                       'bytes': [], 'cycles': [], 'spcr': [], 'selectDriven': True}
        if active and current is not None:
            current['selectDriven'] &= bool(level(e, select, 'ddr'))
            if e['kind'] == 'spi_output':
                current['bytes'].append(e['value'])
                current['cycles'].append(e['cycle'])
                current['spcr'].append(e['spcr'])
        if not active and current is not None:
            current.update(endCycle=e['cycle'], partialEnd=False)
            if current['bytes']:
                groups.append(current)
            current = None
        previous = e
    if current is not None and current['bytes']:
        current.update(endCycle=previous['cycle'], partialEnd=True)
        groups.append(current)
    return groups


def summarize(report, strobe, clock, data, selects):
    simulation = report['simulation']
    trace = simulation['busTrace']
    events = trace['events']
    frames = gpio_frames(events, strobe, clock, data)
    shadow = StledWriteShadow()
    outcomes = Counter(shadow.apply(f) for f in frames)
    patterns = Counter(tuple(f['bytes']) for f in frames if not f['partialStart'])
    groups = {pin: spi_groups(events, pin) for pin in selects}
    return {
        'schema': 1, 'boardEmulated': False, 'physicalMapChanged': False,
        'scope': 'firmware_derived_hypotheses', 'input': report['input'],
        'fixtureHz': simulation['fixtureHz'], 'cycleLimit': simulation['cycleLimit'],
        'traceCoverage': {k: v for k, v in trace.items() if k != 'events'},
        'capturedCycleRange': [events[0]['cycle'], events[-1]['cycle']] if events else None,
        'gpioHypothesis': {'strobe': strobe, 'clock': clock, 'data': data,
                           'sampling': 'rising_LSB_first', 'frameCount': len(frames),
                           'outcomes': dict(outcomes), 'firstFrames': frames[:20],
                           'patterns': [{'bytes': list(k), 'count': v} for k, v in patterns.most_common(30)],
                           'writeShadow': {'pages': shadow.pages, 'displayOn': shadow.display_on}},
        'spiHypotheses': {pin: {'frameCount': len(items), 'firstFrames': items[:12],
                               'lengthCounts': dict(Counter(len(x['bytes']) for x in items)),
                               'patterns': [{'bytes': list(k), 'count': v} for k, v in
                                            Counter(tuple(x['bytes']) for x in items).most_common(16)]}
                          for pin, items in groups.items()},
        'limitations': [
            'Candidate signal assignments are caller-supplied hypotheses, not continuity evidence.',
            'No physical chip identity, panel mapping, voltage, timing parity or module boot is established.',
            'SPI callbacks use the simavr 1.6 fixed 100 us delay, not configured wire timing.',
            'GPIO input-direction bits remain unknown; PIN defaults are not peripheral responses.',
            'Write shadow covers supported STLED commands only; no keyscan/IRQ/read model is attached.',
            'Counts and patterns describe retained events only; inspect truncation and partial frames.'
        ]
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace', type=Path)
    p.add_argument('--strobe', required=True)
    p.add_argument('--clock', required=True)
    p.add_argument('--data', required=True)
    p.add_argument('--spi-select', action='append', default=[])
    args = p.parse_args()
    try:
        raw = args.trace.read_bytes()
        result = summarize(json.loads(raw), args.strobe, args.clock, args.data, args.spi_select)
        result['traceSha256'] = hashlib.sha256(raw).hexdigest()
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
