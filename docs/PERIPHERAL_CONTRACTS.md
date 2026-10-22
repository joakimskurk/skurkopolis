# rev010 peripheral contracts — v0.3.0

This milestone separates three kinds of knowledge that must not be mixed:

1. **Board observation** — what is visibly present on the supplied METROPOLIS Main rev010 photos.
2. **Datasheet contract** — how a candidate IC family behaves in isolation.
3. **Verified board mapping** — which ATmega328 pin is connected to which signal on this specific rev010 board.

Only the first two exist today. The third remains intentionally blank.

## ATmega328-PU

The supplied board photo shows a socketed `ATMEGA328-PU`. Microchip documents the
ATmega328 device signature as `1E 95 14`; ATmega328P is `1E 95 0F`. Fixed PDIP-28 MCU
pin identities are now recorded in `specs/hardware-map.yaml`, but **no board-facing
role, direction or target IC has been assigned**.

The mapping file therefore distinguishes facts such as `pin 17 = PB3/MOSI/OC2A`
from the still-unknown claim “pin 17 drives device X”.

## STLED316S candidate

A supplied photo clearly shows an STLED316S-family display/keyscan device. The ST
datasheet defines a 3-wire interface (`CLK`, `STB`, `DIN/DOUT`), an active-low IRQ,
LED/display memory and an 8x2 key matrix. Key bytes are ordered with SEG1/KS1 at the
LSB and SEG8/KS8 at the MSB. A key-buffer change asserts IRQ_N, and the full key
buffer must be read before IRQ_N clears.

What is **not** known yet:
- which AVR pins are CLK/STB/DIN-DOUT/IRQ_N,
- which panel LED/display element maps to each memory location,
- which physical button maps to each keyscan bit,
- whether any board glue changes polarity or timing.

## 74HC165 candidate

The board photo shows an `HC165AG`-marked device at IC1. The 74HC165 family is an
8-bit parallel-in/serial-out register. Its generic contract includes asynchronous
active-low parallel load, serial shifting on CP low-to-high transitions while CE is
low, and a Q7 serial output.

Board role is unknown. It must not be called a button reader, jack-state reader or
anything else until D0-D7 and control nets are traced.

## 74HC4051D candidate

A supplied photo shows a `74HC4051D` marking. The family is an 8-channel SP8T analog
multiplexer/demultiplexer with S0-S2 select, common Z, Y0-Y7 channels and an enable
input that disconnects all channels when high.

It is plausible for panel ADC multiplexing, but plausibility is not evidence. The
virtual model therefore only tests generic channel-selection semantics.

## Synthetic models

`virtual/synthetic_peripherals.*` contains deliberately generic host-side models for:
- 74HC4051 logical channel selection,
- 74HC165 load/shift behavior,
- STLED316S key-buffer, IRQ and display-memory semantics.

`tests/peripheral_contract_test.cpp` verifies those datasheet-level contracts.
Passing these tests proves **nothing** about rev010 wiring. This distinction is guarded
by `scripts/validate-hardware-spec.py`, which rejects board pin assignments without
explicit evidence.

## Evidence needed before a virtual rev010 board can be claimed

For every board-facing signal we need a row in `specs/hardware-map.yaml` supported by
one or more direct evidence items. Acceptable evidence includes continuity tracing,
clear PCB routing with endpoints visible, passive logic-analyzer capture from the
original firmware, or equivalent schematic-quality measurement.

Priority order:

1. ICSP orientation, MCU signature, fuses and clock source — read-only.
2. STLED316S CLK/STB/DIN-DOUT/IRQ_N to MCU pins.
3. 74HC165 PL/CP/CE/DS/Q7 and D0-D7 destinations.
4. 74HC4051 S0-S2/E/Z/Y0-Y7 routing and ADC settling requirements.
5. External clock/reset input conditioning and edge polarity.
6. Gate/sync digital outputs.
7. Pitch-CV generation path, reference and calibration.
8. Slide/glide and AUX analog paths.

Until at least the digital panel/input/output subset is verified, an original firmware
binary may execute in a CPU model but cannot interact with a faithful Metropolis board.
