# v0.2.0 verification — 2026-10-18

## Passed

1. Local AVR-GCC 5.4.0, AVR libc 2.0.0 and binutils 2.26 toolchain executed successfully.
2. CMake 3.25.2 configured and built native core/trace/tests; CTest passed.
3. CMake `sim` target compiled the AVR probe and native libsimavr runner.
4. AVR test ELF linked for atmega328; HEX produced; memory budget check passed.
5. simavr 1.6 executed 131 independent probe runs. All 16,292 output pulses match
   native output, including 128 consecutive partitions, max 512-pulse phrase,
   skipped/rest stages and all-skipped behavior. Invalid partitions rejected by AVR.
6. 10 Python bridge/HTTP tests passed, including /api/trace/avr with actual simulation.
7. Existing 72,576-pulse native oracle still passed; JavaScript syntax check passed.

Measured instrumented test image: text 1512 + initialized data 18 = 1530 flash bytes;
static SRAM data 18 + bss 257 = 275 bytes. Largest observed post-boot stack: 19 bytes.
Maximum instrumented request across these fixtures: 2828 cycles. These are fixture
measurements, not production totals or real-time timing guarantees.

Machine-readable evidence: artifacts/sim-verification.json, including ELF SHA-256.
Locally extracted package URLs/hashes: artifacts/toolchain-provenance.json.
Packages came from Debian's HTTPS archive; they were not installed into the OS.
No toolchain binaries are redistributed in this project archive.

## Still open

- Docker/Compose launch: no Docker daemon in delivery environment. Dockerfile's
  constituent build/test commands ran locally, but container-level behavior is unproven.
- Browser visual/audio test: Chromium absent; Playwright download returned an HTML
  unavailable page, so the browser suite was not run. Source syntax and HTTP assets pass.
- Exact ATmega328 identity: simavr's shared model reports 328P signature 1e950f.
- Real clock/fuses, rev010 peripherals, GPIO, timer scheduling and analog signal paths.
- Original firmware execution and hardware parity.

The instrumented AVR probe is NOT hardware firmware. Never install it on the module.

## Gate status

M0 evidence dossier: available evidence documented, physical mapping/readout pending.
M1: native + CMake + AVR compile gates PASSED; Docker/browser gate remains OPEN.
M2: original behavior baseline NOT PASSED.
M3: segment test seed only; integration with original behavior NOT PASSED.
M6 prerequisite: actual AVR instruction execution + native parity PASSED.
M6 virtual rev010 board gate: NOT PASSED.
M7 original firmware: NOT STARTED.

Chat length: this step is complete. Before another large implementation step, using
this complete v0.2 package in a new chat would reduce context risk.
