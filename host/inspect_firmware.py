"""Validate a local Intel HEX and inspect an AVR CPU, optionally with synthetic responses."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

FLASH_BYTES = 32768


def parse_hex(raw):
    if len(raw) > 1024 * 1024:
        raise ValueError('HEX exceeds 1 MiB input bound')
    try:
        lines = raw.decode('ascii').splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError('HEX must be ASCII') from exc
    memory = {}
    base = 0
    eof = False
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if eof:
            raise ValueError('Record after EOF')
        if not re.fullmatch(r':[0-9A-Fa-f]+', line) or len(line) % 2 != 1:
            raise ValueError('Malformed HEX at line %d' % line_number)
        row = bytes.fromhex(line[1:])
        if len(row) < 5 or len(row) != row[0] + 5 or sum(row) % 256:
            raise ValueError('HEX length/checksum mismatch at line %d' % line_number)
        size, address, kind = row[0], int.from_bytes(row[1:3], 'big'), row[3]
        data = row[4:-1]
        if kind == 0:
            if address + size > 0x10000 or base + address + size > FLASH_BYTES:
                raise ValueError('Record outside ATmega328 flash')
            for offset, value in enumerate(data, base + address):
                if offset in memory:
                    raise ValueError('Overlapping flash records')
                memory[offset] = value
        elif kind == 1:
            if size or address:
                raise ValueError('Invalid EOF record')
            eof = True
        elif kind in (2, 4):
            if size != 2 or address:
                raise ValueError('Invalid extended-address record')
            base = int.from_bytes(data, 'big') << (4 if kind == 2 else 16)
        else:
            raise ValueError('Unsupported record type %d; no entrypoint assumptions' % kind)
    if not eof or not memory or 0 not in memory or 1 not in memory:
        raise ValueError('Missing EOF, flash content or reset-vector bytes')
    image = bytearray(b'\xff' * FLASH_BYTES)
    for address, value in memory.items():
        image[address] = value
    return bytes(image), {'populatedBytes': len(memory), 'highestAddress': max(memory),
                         'flashCapacity': FLASH_BYTES,
                         'hexSha256': hashlib.sha256(raw).hexdigest(),
                         'paddedFlashSha256': hashlib.sha256(image).hexdigest()}


def inspect(path, runner=None, cycles=2000000, hz=16000000, trace_limit=None, trace_start=0, fixture=None, spi_timing=None, spi_status=None):
    if spi_status not in (None, "avr-master-v1"):
        raise ValueError("Unknown SPI status profile")
    if spi_status and runner is None:
        raise ValueError("SPI status requires a CPU runner")
    if spi_timing not in (None, "avr-divider-v1"):
        raise ValueError("Unknown SPI timing profile")
    if spi_timing and runner is None:
        raise ValueError("SPI timing requires a CPU runner")
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('HEX exceeds 1 MiB input bound')
    image, metadata = parse_hex(path.read_bytes())
    configuration = None
    if fixture is not None:
        if runner is None:
            raise ValueError('A response fixture requires a CPU runner')
        # Lazy path-local import preserves standalone and importlib consumers.
        import importlib.util
        spec = importlib.util.spec_from_file_location('metro_fixture_config', Path(__file__).with_name('fixture_config.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        configuration, fixture_bytes = module.load(fixture)
    result = {'input': metadata, 'boardEmulated': False,
              'limitations': ['No pin mapping or external peripheral responses.',
                              'GPIO/ADC defaults are simulator artifacts, not board observations.',
                              'Register changes sampled after avr_run are not a bus-write trace.',
                              'CPU execution does not establish successful module boot.']}
    if trace_limit is not None:
        if runner is None:
            raise ValueError('Tracing requires a CPU runner')
        if type(trace_limit) is not int or not 1 <= trace_limit <= 100000:
            raise ValueError('Invalid trace capacity')
        if type(trace_start) is not int or not 0 <= trace_start < cycles:
            raise ValueError('Invalid trace start')
    elif trace_start != 0:
        raise ValueError('Trace start requires a trace capacity')
    if configuration is not None:
        result['fixture'] = configuration
        result['fixtureSha256'] = hashlib.sha256(fixture_bytes).hexdigest()
        result['limitations'][0] = 'Explicit synthetic response hypothesis; no verified physical board wiring.'
        result['limitations'] += [
            'Key response is a sampled PINB3 adapter; no electrical line resolution or IRQ is modeled.',
            'SPI replies are synthetic 16-bit words, high byte first; actual ADC identity/packing remains unverified.',
            'SPI timing remains simavr1.6 fixed100us; no external pin-level SPI model.',
            'Key events apply at CPU-run boundaries, without a hardware key-scan debounce model.'
        ]
    if runner is not None:
        if type(cycles) is not int or not 1 <= cycles <= 100000000:
            raise ValueError('Invalid cycle limit')
        if type(hz) is not int or not 100000 <= hz <= 20000000:
            raise ValueError('Invalid fixture frequency')
        with tempfile.TemporaryDirectory(prefix='metropolis-cpu-') as folder:
            binary = Path(folder) / 'flash.bin'
            binary.write_bytes(image)
            command = [str(Path(runner).resolve()), str(binary), str(cycles), str(hz)]
            if trace_limit is not None:
                command += [str(trace_limit), str(trace_start)]
            if configuration is not None:
                fixture_file = Path(folder) / 'fixture.bin'
                fixture_file.write_bytes(fixture_bytes)
                command.append(str(fixture_file))
            if spi_timing:
                command.append("--spi-timing=" + spi_timing)
            if spi_status:
                command.append("--spi-status=" + spi_status)
            proc = subprocess.run(command,
                                  capture_output=True, text=True, timeout=30)
        if proc.returncode not in (0, 2):
            raise RuntimeError('CPU inspector failed: ' + proc.stderr[-2000:])
        result['simulation'] = json.loads(proc.stdout)
        result['runCompletedToLimit'] = proc.returncode == 0
        if trace_limit is not None:
            result['limitations'] += [
                'Bus events are simulator callback observations, not electrical waveforms.',
                'simavr 1.6 SPI completion uses a fixed 100 us timer, not configured SPI clock timing.',
                'Trace PC is the callback-time PC; an asynchronous SPI event is not a write-site PC.'
            ]
    if spi_timing:
        result['limitations'] = [x for x in result['limitations'] if 'fixed100us' not in x and 'fixed 100 us' not in x]
        result['limitations'] += [
            'SPI avr-divider-v1 retimes native simavr byte completion to 8 configured SCK periods.',
            'Native SPIF clearing, collision and slave behavior remain incomplete; no SPI edges, SS or clock/fuse model.',
            'Divider is sampled at SPDR write; completion may be late by an instruction boundary.'
        ]
    if spi_status:
        result['limitations'] = [x for x in result['limitations'] if not x.startswith('Native SPIF') and not x.startswith('SPI avr-divider-v1 retimes')]
        result['limitations'] += [
            'avr-master-v1 models master byte registers, SPIF/WCOL acknowledgement and interrupts; no electrical edges or slave/SS behavior.',
            'Unanswered SPI input is synthetic zero; byte responses use the explicit fixture completion API.',
            'Fixed-100us or divider timing is selected independently; clock/fuses and mid-byte control changes remain unqualified.'
        ]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hex', type=Path)
    parser.add_argument('--runner', type=Path)
    parser.add_argument('--cycles', type=int, default=2000000)
    parser.add_argument('--hz', type=int, default=16000000)
    parser.add_argument('--trace-limit', type=int, help='Capture up to 100000 callback events')
    parser.add_argument('--trace-start', type=int, default=0, help='First eligible cycle')
    parser.add_argument('--fixture', type=Path, help='Explicit synthetic response profile JSON')
    parser.add_argument("--spi-timing", choices=["avr-divider-v1"], help="Opt-in byte completion timing; default preserves simavr 1.6")
    parser.add_argument("--spi-status", choices=["avr-master-v1"], help="Opt-in master register model")
    args = parser.parse_args()
    try:
        result = inspect(args.hex, args.runner, args.cycles, args.hz, args.trace_limit, args.trace_start, args.fixture, args.spi_timing, args.spi_status)
        print(json.dumps(result, indent=2))
        return 0 if result.get('runCompletedToLimit', True) else 2
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'error': str(exc), 'boardEmulated': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
