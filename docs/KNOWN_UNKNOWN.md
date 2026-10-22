# Known unknowns / blocked claims

- Programmer model, ICSP orientation and target-power plan: required before readout.
- IC12 electronic signature, clock/fuses, lock state, EEPROM and FLASH: unread.
- ATmega328 marking predicts signature `1e9514`; that is not a measured board result.
- All MCU-to-board signal connections remain unknown; fixed MCU PDIP pin identities are
  now documented but no board role is assigned.
- STLED316S display/keyscan bus routing and panel memory/bit mapping are unknown.
- HC165 role and PL/CP/CE/DS/Q7/D0-D7 routing are unknown.
- 74HC4051 select/common/channel routing and ADC settling requirements are unknown.
- Pitch DAC/output architecture, reference/calibration, glide control and AUX
  conditioning remain unknown.
- External clock/reset conditioning, active edges, priority and gate/sync output drivers
  remain unknown.
- Physical firmware version and differences from manual 1.30 remain unverified.
- Exact timing, reset edge priority and gate-mode/ratchet interactions require M2/M6 tests.
- simavr aliases atmega328/atmega328p onto a core using iom328p definitions; current
  simulator signature is `1e950f`, not the physical ATmega328 signature `1e9514`.
- Docker launch and browser interaction/audio tests remain open.
- Production firmware memory/stack budgets remain unknown. Instrumented v0.2 probe
  measured 1530 flash/275 static RAM; its post-boot stack observation is not worst-case.
- Musical degree/tetra model and physical gestures remain deferred until the hardware
  and original behavior baselines are strong enough.

No claim of original firmware emulation, drop-in hardware compatibility, microtonal
precision or installation readiness is justified by this package.

v0.4: evidence intake and wiring preflight are implemented, but the registry remains
empty. No new physical facts were inferred. Shared bus fanout/hardwired ties, runtime
simavr binding, serial peripheral timing and trace replay remain unimplemented.

v0.5 clarification: official original firmware 1.37 was obtained and executed in an
unwired CPU. Original firmware availability is no longer blocked; the installed physical
version, real EEPROM/fuses and all electrical connections remain unknown. Toolchain
packages were recovered and custom AVR tests rerun. User lacks hardware access now;
continue offline analysis with explicit hypotheses, not invented map evidence.

## v0.6 clarification

Firmware-derived STLED and SPI-select hypotheses now exist separately from the still
empty physical map. Passive GPIO-frame decoding and a limited STLED write shadow are
implemented. No runtime peripheral response binding is implemented. STLED IRQ/panel
mapping and the actual parts behind SPI select candidates remain unknown.
A confirmed simavr1.6 fixed100us SPI completion prevents real SPI timing claims;
qualifying another timing profile is a separate gate. See BUS_ANALYSIS.md.
