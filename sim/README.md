# Simulator bridge

runner.c executes build/avr/sim-probe.elf on simavr's atmega328 model. Input is 65 bytes;
output is one JSON phrase plus metrics. It does not include the host sequencer library.

Protocol: status 1 ready for configuration; host sets 2 after writing 65 bytes; firmware
sets 3 after configuration; host sets 4 to request a pulse; firmware sets 5 for a pulse,
6 for all-skipped, 7 for rejected configuration. Wire layout is explicit and independent
of struct padding: count(1), segments(24), stages(40). Output: cycle LE32, segment,
repeat, stage, pulse, note, gate count, four pairs of LE16 offset/duration.

A process starts from reset for every trace. This is a finite test bridge, not continuous
live emulation. See docs/AVR_SCOPE.md for the model/signature/timing limitations.
