#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build/avr
avr-g++ -mmcu=atmega328 -std=gnu++11 -Os -g -Wall -Wextra -Werror -fno-exceptions -fno-rtti -ffunction-sections -fdata-sections -Icore core/sequencer.cpp firmware/sim_probe.cpp -Wl,--gc-sections,-Map,build/avr/sim-probe.map -o build/avr/sim-probe.elf
avr-objcopy -O ihex -R .eeprom build/avr/sim-probe.elf build/avr/sim-probe.hex
avr-size build/avr/sim-probe.elf > build/avr/sim-probe-size.txt
python3 scripts/check-size.py build/avr/sim-probe-size.txt
# SIMAVR_PREFIX is only needed for a locally extracted toolchain.
cc -std=c11 -O2 -Wall -Wextra -Werror -I"${SIMAVR_PREFIX:-/usr}/include/simavr" sim/runner.c -L"${SIMAVR_PREFIX:-/usr}/lib/$(cc -dumpmachine)" -lsimavr -o build/sim_runner
