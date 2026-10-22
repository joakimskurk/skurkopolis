# Synthetic response fixture, v0.7.0

## What changed

The original image can now receive deterministic synthetic key and SPI-channel data.
This is an optional, explicitly named hypothesis fixture. It does not populate or
bypass the verified physical map, and does not establish a working Metropolis board.
The unwired default and both custom segment-engine browser routes remain available.

The four 30M-cycle experiments show that independently changing synthetic channel
words and pulsing key bit0 changes the display-memory bytes written by original
firmware. All four repeat exactly and match their corresponding runs without tracing.
The prior v0.6 20M-cycle unwired trace is preserved exactly, including its SHA-256.

## Architecture

`virtual/response_protocol.c` contains simulator-independent state machines:

- STLED write subset, plus command0x49 reading two key bytes LSB first.
- Two independent synthetic eight-channel SPI scan responders.

`sim/response_fixture.c` adapts those models to the pinned simavr1.6 runner. It wraps
existing GPIO/SPCR/SPDR write handlers and calls them exactly once. The fixture is
installed before the passive trace observer and removed after that observer. Each
runner process installs at most one fixture. Baseline runs install none.

`host/fixture_config.py` validates the explicit JSON profile and serializes a small
bounded binary configuration. No untrusted text is evaluated. Unknown or duplicate
fields, booleans in integer slots, invalid lengths and unsorted/oversized event lists
are rejected. The C side checks its magic, truncation, event count/order and trailing
bytes independently. Config is passed as a temporary local file, not shell commands.

## Candidate wiring and scope

| Function | Hypothesis | Adapter behavior |
| --- | --- | --- |
| STLED strobe | PD6, active low | GPIO latch/direction observation |
| STLED clock | PB5, rising command sampling | GPIO edges only while SPE is clear |
| STLED shared data | PB3 | Command writes from output latch; synthetic receive bit substituted in sampled PINB3 reads |
| SPI scan A select | PC5, active low | Eight configurable 16-bit channel words |
| SPI scan B select | PC4, active low | Separate eight configurable 16-bit channel words |
| Other SPI destination | PB2, active low | Observed but deliberately unanswered |

These are firmware-derived assignments, not physical measurements. Key input is a
**sampled PINB3 read adapter**, not an electrical pin driver. It does not implement
pull resistors, GPIO input IRQ propagation, key-scan debounce, STLED IRQ_N or analog
contention. Other bits of PINB are preserved. Direction faults stop the synthetic
reply; there is no simulated contention current or tri-state voltage resolution.

Hardware SPI replies are delivered through SPI_IRQ_INPUT only when the original
simavr SPI_IRQ_OUTPUT completion arrives. Thus SPIF is not raised early by the fixture.
The original fixed100us SPI delay remains unchanged. No SPI clock-edge waveform,
physical baud-rate or CPOL/CPHA timing is claimed.

## STLED transaction subset

A falling strobe begins a frame. Command and write bytes arrive LSB first on rising
clock edges. Already completed write bytes persist when a partial byte is aborted.
Supported writes cover display on/off, the documented page/address sizes, and fixed
or incrementing addresses. No undocumented address wrapping is invented.

Command0x49 (and the equivalent unused-bit7 form) latches the two configured key bytes.
After command bit7, the first falling clock edge makes response bit0 available. The
host must have released PB3. Each subsequent rising edge consumes that bit; after
16 bits the response is complete. A premature strobe rise aborts the remaining bits.
Wrong direction, invalid clock/strobe configuration, SPE enabled during a GPIO frame,
unsupported commands or excess read clocks suppress further replies for that frame.
The fixture never forces the MCU's DDR bits or claims a complete STLED emulation.

Key events replace the two configured bytes at CPU-run boundaries. A read already in
progress keeps its command-time snapshot. Requested and actual application cycles are
reported, with events at or after the stop boundary left unapplied. These are synthetic
input changes without scan/debounce timing, not real switch waveforms.

The standalone v0.6 passive GPIO decoder still marks input-direction bits unknown.
For responding runs, use the fixture summary and actual PINB read events to establish
what the CPU received; output-latch snapshots alone cannot establish receive data.

## SPI response contract

Each candidate scan CS owns its own frame state. First transmitted byte must be one
of 00,08,10,18,20,28,30,38 hex. It selects index0..7 and latches that synthetic word.
The first response is its high byte. A second transmitted00 receives its low byte.
Malformed or additional bytes are rejected until the next frame.

This is an explicit test protocol, not identification of an ADC. Actual hardware may
have different bit packing, conversion latency, pipelining, references or scaling.
The configuration values are raw words; no volts, pitch, sliders or named controls
are assigned. PB2's observed three-byte output has no modeled receiver or DAC output.

Chip select is recorded at SPDR write and checked again at completion, including a
CS-change epoch. Overlapping selects, CS changes mid-byte, overlapping writes or
unsupported master/enable state suppress the reply and increment fault counters.
SPI notification bytes and returned SPDR reads remain separately observable.

## Profiles and reproduction

Build/import the original image as in CPU_INSPECTION.md, then:

```sh
sh scripts/build-inspector.sh
python3 scripts/verify-response-fixture.py
```

The verifier requires the pinned original HEX, compares the unwired v0.6 trace hash,
and runs each scenario twice with tracing and once without it. It writes compact
results under artifacts/ and raw traces only under excluded firmware-local/response-analysis/.

Profiles under `specs/fixtures/`:

| File | Key bytes/events | PC5 / PC4 words |
| --- | --- | --- |
| neutral.json | 0,0 throughout | all zero |
| channel-ramp.json | 0,0 throughout | PC5:0..896 by128; PC4:64..960 by128 |
| key-pulse.json | bit0 on at22M, off at24M | all zero |
| channel-ramp-key-pulse.json | same pulse | same channel ramps |

For one run:

```sh
python3 host/inspect_firmware.py firmware-local/metropolis_1.37.hex --runner build/cpu_inspector --cycles 30000000 --fixture specs/fixtures/key-pulse.json --trace-limit 100000
```

Omitting `--fixture` retains unwired behavior. Trace capacity/start are independent
of the response fixture. User profiles must retain schema1 and profile name
`rev010-hypothesis-v1`; keys have two bytes, each SPI bank has eight words0..65535,
and at most32 strictly ordered key events have cycle0..100M and two byte values.
The JSON schema intentionally offers no physical-verification or arbitrary pin fields.

## Original-image results

| Scenario | Retained events | Complete key reads | Key bit0 seen high | Complete PC5 / PC4 frames |
| --- | --- | --- | --- | --- |
| neutral | 85,477 | 256 | 0 | 2,048 / 255 |
| channel ramp | 85,740 | 257 | 0 | 2,057 / 257 |
| key pulse | 85,581 | 256 | 43 | 2,054 / 256 |
| both | 85,770 | 257 | 43 | 2,060 / 257 |

Every run reaches30M cycles without a reported CPU crash. No selected trace overflows.
No STLED unsupported/direction faults, malformed scan requests or SPI-selection faults
are reported. Each bank sees all eight expected channel word values at the actual
original SPDR read sites. Both key-pulse scenarios yield43 complete reads of word1.

Each scan model counts one empty partial frame during initial DDR/PORT setup. This is
reported instead of hidden; it has no response bytes. A run can also stop in an active
transaction, so response-byte counts need not equal twice the completed-frame count.
The verification report marks incomplete words/bits at the stop boundary separately.
The three unserved initial SPI bytes belong to the intentionally unanswered PB2 path.

Final display page0, in hexadecimal and without panel-order interpretation:

| Scenario | Six display-memory bytes |
| --- | --- |
| neutral | 39 3f 00 20 00 00 |
| channel ramp | 39 3f 00 08 07 00 |
| key pulse | 7c 73 06 5b 3f 00 |
| both | 7c 73 06 5b 3f 00 |

The changed writes are evidence of firmware response to the synthetic inputs. They
are not proof of successful module boot, correct displayed text, physical key identity,
sequencer playback, pitch, gate output or hardware parity.

## Next gate

Qualify an explicit SPI timing profile independently of these input models. Derive
transfer delays from the configured AVR divider and test both normal and double-speed
settings, completion timing and SPIF behavior before comparing original-firmware runs.
Keep simavr1.6's baseline reproducible. Then extend deterministic scenarios to more
input bits and observable output events before building an original-firmware UI.
Actual ADC protocol/packing, STLED IRQ, HC165/4051 roles, physical routing, EEPROM,
fuses/calibration and musical A/B validation remain open.

## v0.8 timing option

The v0.7 results above use native fixed 100 us timing. v0.8 adds an independent opt-in `avr-divider-v1` profile; see SPI_TIMING.md. Default behavior and the archived v0.7 verification report remain unchanged.
