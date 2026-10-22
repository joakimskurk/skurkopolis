# v0.9.0 verification, 2026-10-22

## Delivered and tested

The optional avr-master-v1 register model corrects specific native simavr SPI behaviors while preserving every prior profile. Timing is independently selectable. See SPI_MASTER.md for the exact contract and exclusions.

* 95 Python tests passed with no skips; native core 72,576 oracle pulses, generic peripheral contracts, pure C response-protocol tests and physical evidence validation passed. Log: artifacts/v0.9-tests.txt.
* 17 new CPU tests verify real AVR register reads, write collisions, receive retention, read-only flags, SPIF/WCOL acknowledgement, interrupts, abort/recovery and all divider settings at two frequencies with both timing choices. Each is checked with and without tracing.
* Four new analysis tests cover frame completeness, partial windows, value/count separation and SPI byte pairing.
* Matrix: 32 cases, 96 original-firmware runs. Sweep: 66 cases, 198 runs. All 294 controlled runs complete; every case repeats and has matching traced/untraced CPU reports. Both suites separately verify the unchanged v0.6 unwired startup hash.
* All four archived v0.8 native-divider raw trace hashes remain identical.
* Expected raw key values and channel words reach the CPU in every case. All eight channels are requested on both candidate banks. No protocol faults or trace overflow occurred.
* New-model original runs have zero collisions, ignored non-master writes, aborts or SPI ISR entries; three unserved startup bytes and three unread RX overwrites. Callback lateness is at most one CPU cycle.
* The physical map and evidence registry match the v0.8 git versions byte for byte. No hardware was accessed or written.

## Findings

All 16 status-model comparisons give equal final display pages under matched timing and stop points. These polling-based original-image runs do not exercise the edge cases fixed by the register model; the synthetic CPU programs cover those cases.

Timing changes final display pages for three of eight matched scenario/stop pairs, under either status model. These are channel-ramp at 23.5M and 30M cycles, and combined ramp/key at 23.5M. This isolates an effect of the software timing choice, not physical correctness of either profile.

The single-input sweep confirms all 16 raw key words reach the CPU during their pulse. At 30M cycles, 13 bits produce changed display pages; bits 4, 14 and 15 do not. All 16 single-channel tests deliver their expected values but show no changed final display pages or six-byte display payload sets at the two observation windows. No physical panel labels or musical functions have been assigned.

See INPUT_OBSERVATIONS.md for tables and interpretation. Compact reproducible reports are artifacts/spi-behavior-matrix.json and artifacts/spi-behavior-sweep.json. Aggregate hashes are in artifacts/v0.9-verification.json. Raw traces are ignored under firmware-local/behavior-analysis.

## Limits and remaining gates

Synthetic 16 MHz / 5 V, all-FF EEPROM, default fuses and shared 328/P simulator signature remain. SPI is a master byte/register subset, not an electrical bus model. SS, slave mode, PRR/CLKPR, pin edges, analog input/output, real ADC identity/packing/pipeline, key labels, board clock/fuses/calibration and musical parity remain unverified. Register acknowledgement races at the silicon level and arbitrary mode changes are outside the qualified subset.

Docker/CMake launch and browser/audio acceptance were not run. Browser code changes only the version label; its engine remains our custom sequencer. The prior 131-run native/AVR parity campaign remains v0.5 evidence. No working or 1:1 original Metropolis emulator is claimed.

Next: isolate the timing-sensitive channel effect and qualify input packing/latency before assigning controls to a virtual original-firmware front panel.
