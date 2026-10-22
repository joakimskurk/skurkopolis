# v0.3.0 verification — 2026-10-18

## Package intake

The incoming v0.2.0 `MANIFEST_SHA256.json` was checked before modification: all 54
listed files matched their expected SHA-256 values.

## Passed in this v0.3 session

1. Native C++ core test passed: 72,576 oracle pulses plus reset/validation/skip/rest.
2. New synthetic peripheral tests passed for generic 74HC4051, 74HC165 and STLED316S
   key/display semantics.
3. Hardware metadata guard passed: fixed MCU identities are present and no rev010
   MCU-to-peripheral pin assignment exists without evidence.
4. Python bridge/HTTP tests passed (10 tests, AVR endpoint skipped because no freshly
   built simulator runner exists in this environment).
5. CMake 3.31-class environment configured and built core plus virtual-peripheral
   targets; both CTest tests passed.
6. ATmega328 exact-model discrepancy was resolved at source level: Microchip documents
   signature `1e9514`, while upstream simavr's `sim_mega328.c` uses `iom328p.h` and
   aliases `atmega328` and `atmega328p` to one core. The mismatch remains visible.

## Retained v0.2 AVR evidence

The verified v0.2 artifacts remain unchanged in `artifacts/` and were covered by the
incoming package manifest:

- AVR-GCC target: `atmega328`.
- 131 independent simavr probe runs / 16,292 emitted pulses matched native output.
- Instrumented image: 1,530 bytes flash, 275 bytes static SRAM.
- simavr runtime signature observed: `1e950f`.
- Synthetic fixture frequency: 16 MHz, not measured board frequency.

These AVR results were **not rebuilt in v0.3** because this execution environment lacks
`avr-g++`. Do not reword inherited evidence as a fresh build.

## Browser/Docker status

Docker is not installed in the delivery environment, so Compose remains untested here.
A Chromium executable is now present, but repeated headless navigation attempts did not
produce a usable browser session. Browser interaction/audio is therefore still OPEN;
we do not convert “Chromium exists” into a passed browser gate.

## Gate status

- M0 evidence dossier: component observations + read-only worksheet available; physical
  identity/fuses/mapping pending.
- M1 native/CMake: PASSED. Docker/browser: OPEN.
- M2 original behavior baseline: NOT PASSED.
- M3 segment behavior seed: existing only; original behavior integration NOT PASSED.
- M6 AVR instruction execution prerequisite: PASSED by v0.2 evidence.
- M6 peripheral-contract subgate: PASSED for generic synthetic models only.
- M6 virtual rev010 board: BLOCKED on verified wiring evidence.
- M7 original firmware: NOT STARTED.

The next meaningful progress is physical/read-only mapping evidence, not adding more
sequencer features or inventing pin assignments.
