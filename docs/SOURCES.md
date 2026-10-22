# Sources and evidence

- User photos and original master handoff: included in `evidence/` and `docs/`.
- Intellijel manual v1.30, revision 2020-05-12:
  https://intellijel.com/downloads/manuals/metropolis_manual_1.30_2020.05.12.pdf
  Opened 2026-10-18; panel/pattern pages 9–10 checked for pulse and ratchet scope.
  It is a behavior reference, not evidence that firmware 1.37 is identical.
- simavr upstream: https://github.com/buserror/simavr
  Opened 2026-10-18; reserved for M6. No simulator runtime validated here.
- Future hardware sources, not used to assign board connections:
  https://www.microchip.com/en-us/product/ATmega328
  https://www.st.com/en/power-management/stled316s.html
  https://www.nexperia.com/product/74HC4051DB

Only linked manual references are distributed, not original firmware or copied manuals.

## v0.2 sources

- Debian packaged simavr 1.6 headers, including sim_avr.h and sim_elf.h, read locally.
- Upstream simulator API context: https://github.com/buserror/simavr/blob/master/simavr/sim/run_avr.c
- Local runtime reports, not assumed source behavior, establish the model signature
  and memory geometry shown in artifacts/sim-verification.json.

## v0.3 peripheral/model sources checked 2026-10-18

- Microchip ATmega328 product page:
  https://www.microchip.com/en-us/product/ATmega328
- Microchip signature table (ATmega328 `1E 95 14`, ATmega328P `1E 95 0F`):
  https://onlinedocs.microchip.com/oxy/GUID-CBDC1838-0100-4F26-A45A-134958193C3B-en-US-4/GUID-5A8FB4BC-BC6B-47F2-AACE-6B6B107D5E8A.html
- simavr `sim_mega328.c`; the core names include atmega328/atmega328p and the source
  includes `avr/iom328p.h`:
  https://github.com/buserror/simavr/blob/master/simavr/cores/sim_mega328.c
- STLED316S datasheet/product page, including 3-wire interface and 8x2 keyscan:
  https://www.st.com/en/power-management/stled316s.html
  https://www.st.com/resource/en/datasheet/stled316s.pdf
- Nexperia 74HC165 family description:
  https://www.nexperia.com/product/74HC165BQ
- Nexperia 74HC4051 family description:
  https://www.nexperia.com/product/74HC4051BQ

These sources define component behavior only. They are not evidence of rev010 net
routing beyond the component markings visible in the supplied board photographs.

## v0.5 original CPU work, checked 2026-10-18

- Official support table lists Metropolis 1.37:
  https://intellijel.com/support/
- Linked official archive, downloaded and inspected without executing the updater:
  https://intellijel.com/downloads/firmware/Intellijel_Firmware_Updater_macOS_2025-04-17.zip
  instructions/metropolis.html labels rev009 or higher; application strings associate
  that label with metropolis_ and the older label with metropolis0_. Both plain HEX
  files are present. Archive/member SHA-256 values are recorded in provenance JSON.
- Installed-extraction simavr 1.6 headers supplied API declarations.
- EEPROM ioctl source contract:
  https://raw.githubusercontent.com/buserror/simavr/v1.6/simavr/sim/avr_eeprom.c
- Register addresses were taken from the recovered AVR toolchain headers for the
  target family. Actual report values are direct experimental CPU observations.

No inferred software connection is presented as a measured rev010 net. The package
contains original-firmware metadata/observations but no original firmware or disassembly.

## v0.6 bus analysis, checked 2026-10-20

Pinned simavr1.6 source files sim_core.c, sim_io.c, sim_irq.c, sim_avr.h, avr_ioport.c
and avr_spi.c were downloaded and read locally, along with the STLED316S datasheet
(sections8 and9). Exact source URLs/hashes are in artifacts/bus-analysis-sources.json.
Notably, avr_spi_write schedules a100us completion timer; tests confirm this behavior.
Original image disassembly was inspected locally with the pinned AVR binutils, and
only selected observations are summarized in STATIC_OBSERVATIONS.md. No disassembly
or external source documents are distributed.
