# Skurkopolis / Metropolis Firmware Lab 0.9.0

Original Metropolis 1.37 can receive synthetic key and channel responses in a bounded CPU experiment. An optional SPI timing profile now derives byte completion from the AVR clock-divider registers. The default simavr timing remains unchanged for reproducible comparisons.

**This is not yet a working or 1:1 Metropolis emulator.** Wiring, ADC identity/packing, panel mapping and electrical behavior remain hypotheses. The browser runs our own segment engine. Original firmware, updater binaries and disassembly are excluded.

## New in v0.9

* Opt-in `--spi-status avr-master-v1`: separate transmit/receive state, retained receive data, status-then-data flag acknowledgement, read-only status flags, write-collision rejection and interrupt handling.
* Status behavior and byte timing are independent options. All previous defaults and the four archived v0.8 trace hashes remain unchanged.
* A 2×2 timing/status comparison at identical cycle bounds, plus one-input sweeps of 16 raw key bits and 16 synthetic channels.
* Repeatability, trace-passivity and actual CPU receive-value checks for every experiment. No panel labels are inferred from raw bit numbers.

Read `docs/SPI_MASTER.md`, `docs/INPUT_OBSERVATIONS.md` and `docs/VERIFICATION.md`.

## Existing web lab

```sh
docker compose up --build
```

Open http://localhost:8080. Native and AVR modes retain the custom segment engine. Original-firmware inspection remains CLI-only. Docker launch and browser/audio acceptance were not executed in this milestone.

## Build and tests

```sh
sh scripts/build-sim.sh
sh scripts/build-inspector.sh
RUN_AVR_TESTS=1 RUN_CPU_TESTS=1 sh scripts/test.sh
```

Requires Python 3.9+, g++, AVR GCC/libc/binutils and simavr 1.6 development files. Without AVR/simavr, `sh scripts/test.sh` runs native tests and explicitly skips CPU/AVR integration tests. v0.9 ran all **95 Python tests with no skips**, plus 72,576 native oracle pulses. Existing v0.5 parity reports remain versioned evidence.

## Original-firmware experiments

Follow `docs/CPU_INSPECTION.md` to import the hash-pinned official updater archive. The importer reads ZIP members on any host OS and never executes the updater.

```sh
python3 scripts/import-official-firmware.py /path/to/Intellijel_Firmware_Updater_macOS_2025-04-17.zip
sh scripts/build-inspector.sh
python3 scripts/verify-original-bus.py
```

The verifier reproduces 20M-cycle startup and 80M-cycle late-window experiments. Raw traces remain in excluded `firmware-local/analysis/`; compact observations go in `artifacts/`. Candidate assignments are explicit and are not installed into the verified map. Physical access is unnecessary for this analysis.

Run the synthetic response experiments with:

```sh
python3 scripts/verify-response-fixture.py
python3 scripts/verify-response-fixture.py --spi-timing avr-divider-v1
python3 scripts/verify-spi-behavior.py --suite matrix
python3 scripts/verify-spi-behavior.py --suite sweep
```

Next: investigate the timing-sensitive channel response and qualify input packing/latency before assigning panel controls. Board integration follows verified evidence. Real routing, clock/fuses, EEPROM/calibration, panel mapping and electrical behavior remain open. Included AVR binaries are our simulator probes and must never be flashed onto the module.
