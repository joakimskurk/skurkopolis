# rev010 mapping worksheet

This file is a measurement plan, not a wiring claim. Fill `specs/hardware-map.yaml`
only after each observation is reproducible.

## Session A — read-only MCU identity

Record programmer model, target-power arrangement and ICSP pin-1 orientation first.
Then read only:
- signature,
- low/high/extended fuse,
- lock bits,
- EEPROM,
- FLASH if permitted without erase/write.

Expected marking-based signature is `1E 95 14`, but record the measured value rather
than forcing that expectation.

## Session B — passive digital buses

With original firmware running, attach only high-impedance probes / logic analyzer.
Capture startup plus several deliberate panel actions. Candidate channels:
- STLED CLK, STB, DIN/DOUT, IRQ_N,
- HC165 PL, CP, CE, Q7,
- external clock and reset conditioned nodes,
- gate and sync outputs.

For each channel record voltage range, idle level, edge polarity, repetition rate and
which physical action caused activity. Do not drive candidate nets yet.

## Session C — continuity with module unpowered

Trace MCU pin ↔ candidate IC pin ↔ connector/panel endpoint. For every verified net,
add an evidence token such as `continuity-2026-XX-XX-net03` and the measured endpoints.

## Session D — analog path

Only after digital mapping is stable, trace the 74HC4051 select/common/channel nets and
pitch/AUX/output circuitry. Record reference voltages and settling behavior before any
firmware assumes ADC or CV conversion formulas.

## Gate for virtual-board implementation

A virtual peripheral may be wired to an AVR pin only when that exact connection has at
least one direct evidence item and a confidence level above `unmapped`. Synthetic IC
unit tests never satisfy this gate by themselves.
