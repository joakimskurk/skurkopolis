# ATmega328 exact-model assessment — v0.3.0

## Result

The current simulator path is useful for ATmega328 instruction/register workload
validation, but it is **not an exact ATmega328-PU identity model**.

Microchip documents these signatures:
- ATmega328: `1E 95 14`
- ATmega328P: `1E 95 0F`
- ATmega328PB: `1E 95 16`

Upstream simavr's `sim_mega328.c` declares `SIM_MMCU "atmega328"`, but includes
`avr/iom328p.h` and registers both names `"atmega328"` and `"atmega328p"` on the
same core. This explains why simavr 1.6 accepted `atmega328` while the runtime report
showed signature `1e950f`.

## What this means

The v0.2 AVR parity result remains valid for the tested machine-code workload: the ELF
was compiled with `-mmcu=atmega328`, loaded into simavr and executed with AVR memory
constraints. It does not prove:
- exact non-P device signature behavior,
- fuse/programming identity,
- power behavior,
- oscillator/fuse timing,
- peripheral edge cases where 328 and 328P silicon differ.

The mismatch must remain visible in every simulator report. Do not patch the simulated
signature merely to make the model appear exact.

## Exact-model options

A future exact-identity gate can be closed in one of two defensible ways:

1. Add/maintain a dedicated ATmega328 simavr core definition using the correct device
   identity and verify relevant peripheral/register behavior against the datasheet; or
2. Use a simulator with a separately implemented ATmega328 model and demonstrate the
   expected `1e9514` identity plus required peripheral behavior.

Either option still needs physical read-only discovery from the user's actual IC12.
The board marking is strong evidence, but the electronic signature, fuses and clock
remain unread.

## Sources checked 2026-10-18

- Microchip ATmega328 product documentation and signature table:
  https://www.microchip.com/en-us/product/ATmega328
  https://onlinedocs.microchip.com/oxy/GUID-CBDC1838-0100-4F26-A45A-134958193C3B-en-US-4/GUID-5A8FB4BC-BC6B-47F2-AACE-6B6B107D5E8A.html
- simavr upstream `sim_mega328.c`:
  https://github.com/buserror/simavr/blob/master/simavr/cores/sim_mega328.c
