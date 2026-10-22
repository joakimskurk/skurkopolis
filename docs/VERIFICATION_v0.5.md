# v0.5.0 verification, 2026-10-18

## Actual new milestone

Official original Metropolis firmware 1.37 for rev009-or-higher was obtained from the
Intellijel updater archive, validated and executed in an unwired simavr CPU. This is
not a virtual rev010 board and does not certify module boot or original behavior.
No firmware bytes, updater archive or disassembly are redistributed here.

## Fresh tests and experiments

- C++ native core: 72,576 oracle pulses plus existing regression checks passed.
- Existing generic synthetic peripheral tests passed.
- Strict real-map evidence validation passed: still zero assigned board pins.
- Python: 45 tests passed, no skips. Includes 23 evidence tests, 12 HEX/CPU tests and
  10 bridge/HTTP tests, including the real AVR endpoint.
- Inspector test programs are our synthetic RJMP loop and known DDRB write; their
  deterministic PC counts and observed register change passed. No proprietary test
  firmware is needed to run the suite.
- Current AVR-GCC build of our mailbox probe passed size checks. simavr parity was
  rerun: 131 runs, 16,292 pulses matching native; max instrumented request 2,828 cycles;
  observed post-boot stack 19 bytes. These are fresh results, not inherited v0.2 claims.
- Custom test image: 1,530 flash bytes, 275 static SRAM bytes. Rebuilt ELF/HEX and its
  matching verification report replace the prior compiled probe artifacts.
- Original image: 20,710 populated flash bytes. HEX checksum/extent validated.
- Original CPU runs: 2M, 16M and 80M cycle budgets, no reported CPU crashes. Observed
  cycles were 2,000,002; 16,000,000; 80,000,000. The 16M and 80M runs were repeated
  independently and their complete reports matched exactly.

Details: artifacts/cpu-inspector-verification.json, artifacts/original-cpu-*.json,
artifacts/original-firmware-provenance.json, artifacts/sim-verification.json and
artifacts/v0.5-tests.txt. The register observations did not change physical mapping.

## Toolchain recovery

AVR GCC, binutils, AVR libc and simavr packages were retrieved from the previously
recorded Debian URLs. Every archive hash matched artifacts/toolchain-provenance.json
before local extraction. They were not installed system-wide or included in this ZIP.
The source-level EEPROM ioctl contract was checked against simavr v1.6 avr_eeprom.c:
GET requires a caller-provided range and handled operations may still return -1.
The inspector verifies EEPROM bytes rather than treating that return code as success.

CMake and Docker remain unavailable in the current runtime. Their targets/build recipe
were updated but not executed. No new browser/audio test is claimed. The inherited JS
syntax result remains unchanged; only the visible version label changed.

## Interpretation limits

The original image runs with 16 MHz/5 V synthetic settings, default simulator fuses,
all-0xff initial EEPROM, no board wiring and no external peripheral responses.
The model still reports 1e950f, not the target ATmega328 identity 1e9514. CPU progress
and repeatability are not hardware parity. Register-change counters are sampled state
changes, not a complete bus-write trace. An instruction may cross the cycle limit.
There is no original-firmware web playback mode or continuous interactive emulator.

## Gates and next work

- M1 native/HTTP/AVR: passed; Docker/CMake execution not rerun here, browser gate open.
- M2 manual baseline and M3 integration: not passed.
- M6 CPU execution, generic contract tests and mapping preflight: passed at their
  explicitly limited scopes. Physical map, wire-level devices and board integration open.
- M7 original-firmware CPU prerequisite: now demonstrated. Usable original-module
  emulation and behavior A/B gate remain open.

User currently has no measurement equipment and programmer is unavailable. Continue
software-only protocol/static analysis and mark any connection hypotheses explicitly.
Do not repeatedly demand hardware access or create guessed verified nets.

Chat length: two substantive milestones and complete intake have now accumulated.
This is a good migration boundary before another large simulator implementation.
The archive includes complete source and an updated NEXT_CHAT_PROMPT.txt.
