# v0.6.0 verification, 2026-10-20

## Fresh results

- Input v0.5 archive: all 86 manifest entries SHA-256 verified before editing.
- Six recovered Debian toolchain packages and official updater archive matched recorded hashes. Original HEX matched the pinned rev009+ 1.37 hash.
- C inspector rebuilt with `-Wall -Wextra -Werror`; custom AVR probe rebuilt locally.
- Native core: 72,576 oracle pulses plus existing regression checks passed.
- Generic peripheral contracts and evidence validator passed: zero assigned physical pins and zero reviewed records, with map/registry unchanged.
- Python: 58 tests passed, no skips, including existing AVR endpoint and CPU-runner tests. Log: `artifacts/v0.6-tests.txt`.
- Thirteen new tests cover equal writes, original PIN-toggle handler forwarding, bounds, late capture, duplicate SPI notifications, fixed SPI delay, argument guards, LSB order, released data, partial frames, SPE/direction gating, STLED writes, CS grouping and static-I/O parsing.
- Original image: fresh baseline plus two traced runs per experiment. Startup: 20M cycles, 13,414 events. Late: 80M cycles, capturing from 78M, 14,164 events. No selected window overflowed.
- Each repeated parsed report was identical. Each traced CPU report, excluding the trace field, equalled its fresh untraced baseline. This is observed-report parity, not equivalence of every internal simulator field.

Reports: `original-bus-verification.json`, `original-bus-startup.json`, `original-bus-late.json` and `bus-analysis-sources.json` under `artifacts/`. Raw traces remain private/local and are recreated by `scripts/verify-original-bus.py`. Neither original bytes nor disassembly are bundled.

## Scope and retained limitations

Synthetic 16 MHz / 5 V fixture; all-FF initial EEPROM; default simulator fuses; shared model signature 1e950f, not expected physical 1e9514. No original-board wiring or external responses are attached. No module boot, panel mapping, musical behavior, pitch or gate timing is certified.

simavr 1.6 schedules SPI completion at fixed 100 us. Source inspection and a synthetic two-identical-byte test confirm this. Byte notifications are not electrical SPI edges. GPIO snapshots are latch/direction state. Internal peripheral updates outside wrapped callbacks are not captured. Read/modify/write callback counts are not pin pulses.

The STLED decoder is a passive write subset, not a complete responding device. It retains unknown receive bits and partial boundaries. Chip identities behind SPI select candidates remain unknown. The physical evidence map has not been populated with inferred assignments.

The prior 131-run/16,292-pulse native/AVR parity campaign remains a **v0.5** result; it was not repeated because sequencer/custom-runner sources are unchanged. v0.6 ran AVR endpoint integration tests on the fresh custom build. Docker/CMake launch and browser/audio acceptance were not run. Frontend changes are only the version label.

## Gates

The bounded analysis tools and synthetic decoding tests pass. Original module emulation, physical wiring, responding models, real timing and A/B behavior gates remain open. Next: separate synthetic response fixtures and a qualified SPI timing profile.
