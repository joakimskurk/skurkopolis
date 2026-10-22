# Bus observations and protocol hypotheses, v0.6.0

## Result

The pinned original Metropolis 1.37 image now has reproducible, bounded I/O callback
traces. A candidate three-wire channel decodes into coherent STLED316S commands,
including display enable, six-byte display-memory writes and two-byte key-read
requests. Three candidate SPI select lines delimit repeated byte transactions.
These are firmware-derived hypotheses. **No physical map entries were changed.**

The separate native/AVR segment engine and the browser continue unchanged in function.
This milestone adds analysis tools, not an interactive original-firmware emulator.

## What the trace means

`sim/bus_trace.c` wraps existing simavr 1.6 read/write callbacks for PIN/DDR/PORT B–D,
SPI and ADC registers, calls each existing handler exactly once, then records the
observed value and GPIO latch/direction snapshots. Registers without a handler retain
their default data-array behavior. Equal-value writes are recorded. Reads of PINx,
SPDR and ADC registers are retained; other selected reads are counted only to avoid
filling the trace with status polling and GPIO read/modify/write overhead.

SPI output events come separately from SPI_IRQ_OUTPUT. They describe the simulator's
byte notification, not eight clock edges. The trace never drives an input, fabricates
an external response, replaces a device model, or changes IRQ filtering flags.

Events carry cycle, callback-time PC, access address/value, PORTB/C/D, DDRB/C/D,
SPCR and SPSR. Synchronous write PCs identify observed instruction sites. A SPI
completion PC is the current PC when the timer callback runs, not the initiating
write site. GPIO snapshots are latches/directions, not resolved electrical voltages.
SBI/CBI may appear as both reads and writes internally; counters are callbacks, not
a universal count of physical bus transactions. Internal peripheral changes that do
not pass through these callbacks are outside the trace.

Capacity is 1–100,000 events. An optional start cycle selects a late window. The CPU
continues after capacity is exhausted; `dropped` and `truncated` expose lost events.
`beforeWindow`, `countOnlyReads` and access counts are whole-run counters, whereas
decoded frames describe retained events only. The start filter does not reset the
CPU or peripherals. Only one process-local trace session is installed per runner.

## A timing limitation uncovered

The recovered simavr 1.6 SPI source schedules completion with a fixed 100 microsecond
timer. It does not derive that delay from SPI clock configuration. At the declared
16 MHz fixture this is about 1,600 cycles per byte. Our synthetic two-byte test
confirms that observation, including delivery of identical consecutive bytes.

Consequently, firmware polling time, scheduling interactions and aggregate throughput
in these experiments are **not real Metropolis timing**. No simulator timing patch
is silently applied. A future correction requires a separate tested profile and new
baselines. Hardware SPI pin waveforms are not reconstructed from PORT latches.

## Candidate signal relationships

All PCs below are byte addresses in the pinned image. They are analysis landmarks,
not source symbols, exhaustive routine boundaries or measured board connections.

| Hypothesis | Software observations | Remaining uncertainty |
| --- | --- | --- |
| STLED-like STB=PD6, CLK=PB5, bidirectional DATA=PB3 | Repeated GPIO sequences around 0x042e–0x081a; 0x06c0 output path and 0x0752 read-request path; LSB-first traffic decodes coherently | Physical endpoints, IRQ routing, panel/segment order and electrical timing |
| PB2 as active-low SPI select | Startup path 0x0350 and update path 0x0394; observed startup bytes 30 00 00 hexadecimal | Actual part and output role; a DAC-like protocol is only a hypothesis |
| PC5 as active-low SPI select | Path 0x03d2 drives CS low, sends channel-like values 08..38,00 followed by 00, reads two SPDR values, then releases CS | Part identity, channel mapping, response packing and physical analog inputs |
| PC4 as another active-low SPI select | Accesses around 0x4662–0x4686 use the same two-byte command family | Whether the destination is a second converter and how it is connected |

PB5/PB3 are reused by GPIO bit-banging with SPE clear and by hardware SPI paths.
This is a software observation, not proof of shared board routing. The static tool
does not resolve indirect calls, pointer-based I/O or all branch paths. Selected
absolute callers and dynamic write-site PCs are used together; neither proves full
control-flow coverage. `docs/STATIC_OBSERVATIONS.md` lists the selected call sites.

## Reproduced windows

| Experiment | CPU cycles | Retained window | Events | SPI callbacks, whole run | GPIO frames |
| --- | --- | --- | --- | --- | --- |
| startup | 20,000,000 | from reset | 13,414 | 703 | 89 |
| late | 80,000,000 | from 78,000,000 | 14,164 | 23,577 | 90 |

Both traces repeat byte-for-byte at the parsed-report level. In each experiment the
CPU report with tracing removed matches a fresh untraced run. This checks the report's
registers, PC samples, counts and stop reason; it is not proof of equivalence of every
hidden simulator field. Neither selected window overflowed. The start of the startup
trace includes an already-low strobe and is marked partial, not interpreted as a command.

With the candidate STLED mapping, startup includes commands 0x30, 0x11, 0x0d, 0x00,
0x28 and 0x49. There are 39 startup and 42 late requests of the form
`[0x49, unknown, unknown]`: the MCU releases PB3 for the 16 receive clocks. The decoder
preserves those bits as unknown rather than interpreting pull-ups as actual key data.
Known display-memory writes can be reconstructed, but the panel's physical order,
labels and current state are not established by this.

Startup SPI grouping yields one PB2 frame of three bytes, 312 PC5 frames of two bytes,
and 38 PC4 frames of two bytes. Late grouping yields 340 PC5 and 42 PC4 frames of two
bytes. The PC5/PC4 patterns cycle through eight command values in steps of eight.
Grouping is performed independently per candidate CS, so overlapping active selects
would not establish a unique destination.

## Decoder and write shadow

`host/analyze_bus.py` requires explicit candidate signals; it never loads them from
the verified hardware map. The GPIO decoder samples rising clock edges LSB first,
within active-low strobe frames, with SPE clear and driven clock/strobe. Partial
starts/ends and trailing bits remain visible. Released data bits become `null`.

`StledWriteShadow` implements only the documented write-command subset: memory page,
address, fixed/auto-increment, display on/off and completed-byte retention. It stops
at unsupported addresses rather than inventing wrap behavior. Its unknown initial
state remains `null`, appropriate for a window into an already-running device. It
does not supply key data, scan a keyboard, drive DIN/DOUT or IRQ, or implement display
timing. It is a passive decoding aid, not a complete STLED316S emulator.

## Reproduction

Import the pinned official archive and build as described in `CPU_INSPECTION.md`, then:

```sh
sh scripts/build-inspector.sh
python3 scripts/verify-original-bus.py
python3 host/inspect_io_sites.py firmware-local/metropolis_1.37.hex --entry 0x350 --entry 0x394 --entry 0x3d2 --entry 0x6c0 --entry 0x752
```

The verifier writes raw traces only under excluded `firmware-local/analysis/` and
compact reports under `artifacts/`. Inspect an individual trace with explicit hypotheses:

```sh
python3 host/analyze_bus.py firmware-local/analysis/startup-trace.json --strobe PD6 --clock PB5 --data PB3 --spi-select PB2 --spi-select PC5 --spi-select PC4
```

Custom windows use `host/inspect_firmware.py --runner build/cpu_inspector --cycles ...
--trace-limit ... --trace-start ...`. A trace requires a runner and a start below the
cycle limit. Exit on CPU crash remains distinct from successful completion.

## Next implementation gate

Build an explicitly synthetic response fixture, initially for STLED key reads and
the two SPI channel-scan candidates. Keep its assumed pin assignments in a separate
hypothesis profile, never the evidence-backed map. Validate data direction, contention,
clock edges and response packing with synthetic programs before applying it to the
original image. Resolve the SPI timing model separately. Continue preserving the
unwired baseline. HC165/4051 board integration, actual EEPROM/calibration/fuses and
physical measurements remain open; no hardware access is required for this software work.
