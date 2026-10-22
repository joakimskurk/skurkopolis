# v0.8.0 verification, 2026-10-22

## Results

* Inspector rebuilt with -Wall -Wextra -Werror against the recorded simavr 1.6 toolchain.
* 74 Python tests passed without skips; 72,576 native oracle pulses, generic peripheral contracts and pure C response-protocol tests passed. See artifacts/v0.8-tests.txt.
* Six new integration tests cover all eight SPI divider settings at two CPU frequencies, equal bytes, traced/untraced parity, SPIF polling with received bytes, busy-write accounting, disable behavior, latched divider and argument validation.
* Original 1.37: four scenarios, each twice traced and once untraced, to 23.5M cycles. Complete trace window: 23M through 23.5M, 9,814 to 9,948 events. All reports repeated exactly and matched untraced reports after removing the trace field.
* Expected synthetic key words and all configured channel words reached the CPU. Zero fixture protocol faults, busy SPI writes or non-master writes. All observed transfers used divide-by-4 (32 cycles per byte); native callback lateness was at most one cycle.
* The original unwired v0.6 20M startup trace retains SHA-256 9c474fa8744ea93cae9abc51e5e31b5e8cd2362bf4518c36af26e292d7519ead.
* Verified physical map and evidence registry remain unpopulated and unchanged. Native/custom AVR browser behavior is unchanged; only its version label advances.

Compact results: artifacts/spi-timing-verification.json. Raw traces are ignored under firmware-local/timing-analysis. Reproduce with scripts/verify-response-fixture.py --spi-timing avr-divider-v1 after importing the pinned official archive.

## Interpretation

At the v0.8 stop point, display page zero is 39 3f 00 00 08 00 hex in every scenario. Synthetic inputs demonstrably reach the firmware, but no changed display state at this stop point or successful module boot is claimed. Archived v0.7 fixed-100-us experiments at 30M cycles had differing display states; those runs use a different stop point and cannot isolate timing as the sole cause.

The original 9M trace window exceeded the event cap. Reducing the observation window to 0.5M preserves complete capture and includes the active key pulse. Window-boundary partial transactions are recorded separately from complete input words; counters from the entire run are not compared as if they covered the window alone.

## Limits

The optional profile changes byte completion timing only. Native simavr SPIF clearing, WCOL/collision and slave limitations remain. Timer/module-layout dependency is checked at runtime. The default profile and old report format are preserved. See SPI_TIMING.md for model details.

No physical wiring, oscillator/fuses, ADC device/packing, panel/key label, EEPROM/calibration, pitch/gate timing or musical parity is verified. CPU signature remains the simulator's shared 328/P model. No hardware was flashed. Original firmware/updater/disassembly are excluded.

Docker/CMake launch and browser/audio acceptance were not run. The 131-run native/AVR parity campaign remains v0.5 evidence; the current suite includes AVR endpoint integration tests. v0.7 response-fixture results are archived in VERIFICATION_v0.7.md.

Next: qualify status-register behavior and correlate controlled inputs with firmware display/sequence behavior, keeping hypotheses separate from verified hardware evidence.
