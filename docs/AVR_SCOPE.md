# What the AVR path does and does not prove

The AVR compiler emits machine code for ATmega328. simavr loads that compiled ELF
into its flash model and executes instructions. A byte mailbox in simulated SRAM
provides configuration and retrieves pulse results. This is not a host implementation
pretending to be an AVR. Host-side Engine::next is not linked into the simulator runner.

The firmware includes the same C++ core source as native, but it is independently
compiled for the AVR instruction set. Parity tests compare complete emitted events.

## Enforced / measured

- Simulator memory geometry checked at startup: flash 32768, SRAM 2048, EEPROM 1024.
- ELF bounds checked before loading into the model; static RAM budget 1200 bytes.
- Build budget: flash below 26 KiB, static RAM below 1200 bytes.
- Mailbox symbols must point inside SRAM and are bounds checked.
- Each handshake has a two-million-cycle deadline; at most 513 pulse requests.
- Python adds a five-second process timeout; no silent switch to native on failure.
- Model execution counts and post-boot observed stack-pointer low-water mark reported.
- No original firmware is accepted by this instrumented runner: it needs our mailbox
  symbols and protocol. The UI has no original-HEX upload option.

## Model limitations

simavr 1.6 accepts the requested model name atmega328 but internally reports signature
1e950f, the 328P signature. We did not patch it to impersonate the real chip. This
precludes claims about exact device identity, fuses, programming or power behavior.
The model can test this instruction/core workload; it is not a chip qualification.

Frequency is a declared 16 MHz test fixture, unrelated to unmeasured board fuses.
Gate offsets are still abstract 120-tick pulse plans. No timers or GPIO drive those
plans yet. `maxRequestCycles` includes polling and mailbox encoding and must NOT be
presented as gate jitter, interrupt latency or a maximum production execution time.

The observed stack excludes boot/global constructors and only covers tested paths.
It is not a worst-case stack proof. Physical voltage accuracy, analog glide, clock
conditioning, display scanning, buttons, ADC/mux wiring and EEPROM behavior are absent.

## Why this milestone matters

Previously only host code ran. Now the code is compiled to AVR, runs in a constrained
CPU model and produces measured parity results. The remaining big gap is the board,
not another musical feature. M6's virtual-board gate remains OPEN.

## v0.5 original CPU inspector

The instrumented runner described above still accepts only our probe. A separate
sim/inspect_cpu.c now accepts strictly validated, padded flash through
host/inspect_firmware.py. It has executed the official original rev009+ 1.37 image,
without virtual-board connections. This does not remove any model or electrical limit.
The mailbox probe was also freshly rebuilt and parity-tested in v0.5.

## v0.6 trace scope

Original firmware now has optional callback bus traces and passive protocol decoding.
No board model is attached. The new synthetic tests confirm identical-write capture
and simavr1.6 fixed100us SPI completion. That delay is not hardware timing.
Custom sequencer/probe behavior is unchanged; full v0.5 AVR parity figures are retained
historical evidence, with fresh v0.6 endpoint integration tests.
