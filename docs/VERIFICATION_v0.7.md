# v0.7.0 verification, 2026-10-20

Synthetic response fixture implemented and verified before the v0.8 timing work.
See RESPONSE_FIXTURE.md and artifacts/response-fixture-verification.json.

* 68 Python tests passed without skips, plus 72,576 native oracle pulses and pure C response protocol tests. Log: artifacts/v0.7-tests.txt.
* Four 30M-cycle scenarios, each repeated twice with tracing and once without: neutral, channel ramp, key pulse, combined. All completed, repeated exactly, matched untraced reports, and had no protocol faults or trace overflow.
* Original firmware read expected synthetic key and channel values. Display RAM changed with controlled stimuli. This is not proof of module boot or musical correctness.
* v0.6 unwired 20M startup trace SHA-256 remained 9c474fa8744ea93cae9abc51e5e31b5e8cd2362bf4518c36af26e292d7519ead.
* Physical map and evidence registry unchanged. Native/custom AVR browser engines unchanged in function.

SPI remained at native simavr 1.6 fixed 100 us. GPIO input was a sampled PINB3 adapter; actual nets, ADC packing, key labels, electrical behavior, fuses and calibration remained unknown. Docker/CMake and browser/audio acceptance were not run. Prior 131-run native/AVR parity campaign remains v0.5 evidence.
