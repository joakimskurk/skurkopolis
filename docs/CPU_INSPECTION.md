# Original firmware CPU inspection, v0.5

The user has no measurement equipment available now and the programmer is elsewhere.
Physical discovery is deferred. Software-only progress is possible: the original HEX
can execute on an unwired CPU, and its register behavior can be observed without
inventing board connections. This is a different scope from a virtual Metropolis.

## Official source and revision selection

Intellijel's support page currently lists Metropolis 1.37 and links the legacy updater:
https://intellijel.com/support/
https://intellijel.com/downloads/firmware/Intellijel_Firmware_Updater_macOS_2025-04-17.zip

The archive contains plain HEX files in the macOS app resources; no application was
executed. The extracted instructions identify rev009 or higher, and updater strings
associate that family with the metropolis_ prefix. Older rev008-and-below hardware
uses metropolis0_. Our rev010 candidate is metropolis_1.37.hex, with 20,710 populated
flash bytes. This does not establish which version is installed in the physical unit.
Source and content hashes are in artifacts/original-firmware-provenance.json.
Original files and disassembly are deliberately absent from the project distribution.

## Local reproduction

Download the ZIP linked above directly from Intellijel, on Windows, Linux or macOS.
The importer reads archive members, so it does not need macOS and does not run the app.

```
python3 scripts/import-official-firmware.py /path/to/Intellijel_Firmware_Updater_macOS_2025-04-17.zip
python3 host/inspect_firmware.py firmware-local/metropolis_1.37.hex
sh scripts/build-inspector.sh
python3 host/inspect_firmware.py firmware-local/metropolis_1.37.hex --runner build/cpu_inspector --cycles 80000000 --hz 16000000
```

The importer checks the exact inspected archive and member hashes before extraction.
A changed archive is rejected, requiring inspection rather than bypassing the checks.
The output stays in firmware-local. It refuses to overwrite a different firmware file.
Never package that directory's contents or original Intellijel firmware with a release.
The strict HEX parser checks checksums, record lengths/types, nonoverlap, flash bounds,
EOF and reset bytes. Missing flash addresses are explicitly padded with 0xff.
The inspector accepts a full 32,768-byte decoded image; it requires no ELF symbols or
mailbox. It does not modify the existing custom-probe route in sim/runner.c.

Build requirements: C compiler and libsimavr development headers/library. AVR GCC is
needed for rebuilding the custom test firmware but not for loading the original HEX.
SIMAVR_PREFIX can select a locally extracted /usr; LD_LIBRARY_PATH must point at its
lib/<compiler-triplet> directory if it is not installed system-wide.

## Experiment conditions

- Requested MCU: atmega328. simavr 1.6 reports shared-model signature 1e950f.
- Geometry checked: 32,768 flash, 2,048 SRAM, 1,024 EEPROM bytes.
- Clock: synthetic 16 MHz; voltage references: synthetic 5,000 mV.
- EEPROM: explicit all-0xff initial contents, verified in simulator memory.
- Fuses: simulator defaults. None came from the physical module.
- No external GPIO, ADC, STLED, HC165, mux or CV circuit is connected.
- No programmer/device connection or hardware writes occur.

All-0xff EEPROM is an experiment condition, not the user's preset/calibration state.
The firmware may change its simulated EEPROM while running; it is reset for each run.
A physical backup, measured clock, actual fuse configuration and proper peripheral
responses will be needed for faithful behavior later.

## Results

| Cycle budget | Observed cycles | Stop | Repeat |
| --- | --- | --- | --- |
| 2,000,000 | 2,000,002 | cycle limit | not repeated |
| 16,000,000 | 16,000,000 | cycle limit | identical report |
| 80,000,000 | 80,000,000 | cycle limit | identical report |

The two-cycle overshoot is instruction completion, not a timing failure.
At the final 80M sample, observed values include DDRB=0x2c, DDRC=0x3f, DDRD=0xe3,
EIMSK=0x03, SPCR=0x50, TIMSK1=0x02 and TCCR1B=0x0a. Some of these differ from the
16M sample, so the longer run exposes later initialization/activity. These are CPU
register observations only; they do not establish which board component is connected.
No board map entries or reviewed physical evidence were added from this experiment.

The runner samples selected memory-mapped register values after avr_run returns. It
counts observed value changes, not bus writes. Equal-value writes, some within-call
activity and external electrical behavior are outside its scope. PC histograms count
run-call samples and are not full control-flow or coverage proofs. The 16 MHz conversion
of 80M cycles is five seconds of fixture time, not a claim about the real module clock.

No CPU crash was reported before the selected limits. This does not establish successful
module boot, correct display, sequencer operation, clock accuracy, pitch, gate or UI.

## Boundaries and next software step

The physical-map evidence gate remains intact. Firmware-derived hypotheses should go
in a separate analysis document, never be silently promoted to continuity evidence.
Next: use bounded traces/static analysis to identify peripheral transaction patterns;
implement wire-level synthetic protocol tests independently of rev010 pin mapping.
Keep the fixed synthetic clock, model identity mismatch and missing board state visible.
When physical access returns, compare those hypotheses with real observations.

The CPU inspector currently runs from CLI only. The browser AVR selector still executes
our own mailbox probe, not the original firmware. No original-firmware playback UI exists.
