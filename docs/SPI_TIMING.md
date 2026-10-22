# Optional SPI byte timing, v0.8.0

## Usage

```sh
sh scripts/build-inspector.sh
python3 host/inspect_firmware.py firmware-local/metropolis_1.37.hex \
  --runner build/cpu_inspector --cycles 23500000 \
  --fixture specs/fixtures/channel-ramp-key-pulse.json \
  --trace-limit 100000 --trace-start 23000000 --spi-timing avr-divider-v1
python3 scripts/verify-response-fixture.py --spi-timing avr-divider-v1
```

Omitting the timing option preserves native simavr 1.6 fixed 100 us behavior and the previous report format. Timing is independent of the response fixture and does not update the verified physical map.

## Model

SPCR.SPR1:0 and SPSR.SPI2X select the divider. At SPDR write, the adapter schedules byte completion after eight divider periods, measured in simulator CPU cycles:

| SPI2X | SPR1:0 | Divider | Byte cycles |
|---|---|---|---|
| 0 | 00 | 4 | 32 |
| 0 | 01 | 16 | 128 |
| 0 | 10 | 64 | 512 |
| 0 | 11 | 128 | 1024 |
| 1 | 00 | 2 | 16 |
| 1 | 01 | 8 | 64 |
| 1 | 10 | 32 | 256 |
| 1 | 11 | 64 | 512 |

Source: Microchip ATmega328P datasheet 7810D, SPI register description (18.5), https://ww1.microchip.com/downloads/en/devicedoc/atmel-7810-automotive-microcontrollers-atmega328p_datasheet.pdf. This supports the divider calculation for the simulator's shared 328/P model; it does not establish the board clock or physical MCU configuration.

`sim/spi_timing.c` installs before response and trace hooks. It forwards each SPDR write to the native handler, finds that SPI module's scheduled timer, checks the fixed 100 us deadline, cancels that timer and reschedules its original callback through a small accounting wrapper. Native byte notifications and input response handling remain in use. Missing/ambiguous timers or a changed timer function cause an explicit error. This depends on simavr 1.6 timer/module structures, not a portable simulator extension API. Source provenance for simavr is in artifacts/bus-analysis-sources.json.

Hooks are removed in reverse order. One profile is installed per runner process. No simavr installation or global library files are patched.

## Scope

This is a byte-completion timing hypothesis, not an electrical SPI implementation. CPOL/CPHA edges, SS behavior, PRR, CLKPR, oscillator/fuses and external device latency are not modeled here. Divider changes during a byte take effect on the next SPDR write. Timers fire on simulator instruction boundaries and can be slightly late.

Native simavr 1.6 status behavior remains: SPDR reads clear SPIF even without a preceding SPSR read; busy SPDR writes overwrite/restart instead of implementing hardware WCOL. Busy writes are counted and cancel/restart the adapter timer consistently with native behavior. Disabled/slave writes are counted as nonMasterWrites. Native completion suppresses SPI output when SPE/MSTR are absent at completion. Therefore timerCallbacks counts scheduled callbacks, not necessarily completed bus bytes. No hardware flag-conformance claim is made.

## Verification

The focused CPU tests cover all eight settings at 8 and 16 MHz, repeated equal-byte notifications, traced/untraced parity, firmware SPIF polling with actual synthetic receive values, busy-write accounting, disabled completion, divider sampling and instruction-boundary lateness. Existing default-timing tests continue to pass.

Original-image experiments run to 23.5M cycles with a complete 23M to 23.5M trace window. This intentionally observes the active key pulse (22M to 24M). Partial input transactions crossing either window boundary are recorded and excluded from complete-word counts. Full-run fixture counters and window-only CPU-read counts have different scopes. Four scenarios each run twice traced and once untraced. The verifier checks repeatability, report parity, expected CPU receive words, no protocol faults, and zero busy/non-master writes. Raw traces stay in ignored firmware-local/timing-analysis; the compact report is artifacts/spi-timing-verification.json.

A 9M-cycle trace window exceeded the bounded 100,000-event buffer; the final window is 0.5M cycles. This was a capture-capacity failure, not a CPU failure. No truncated trace is accepted by the verifier.

The unchanged v0.6 unwired startup trace is hash-checked on every verification run. Display-memory changes under stimuli do not establish successful module boot, panel mapping, pitch/gate timing or musical parity.

At the 23.5M-cycle stop point, all four scenarios have identical display page zero (39 3f 00 00 08 00 hex). The v0.7 runs stopped at 30M and are not a controlled same-time timing comparison.
