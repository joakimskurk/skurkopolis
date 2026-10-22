#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build/avr
avr-g++ -mmcu=atmega328 -std=gnu++11 -Os -Wall -Wextra -Werror -fno-exceptions -fno-rtti -ffunction-sections -fdata-sections -Icore core/sequencer.cpp firmware/smoke.cpp -Wl,--gc-sections,-Map,build/avr/compile-only.map -o build/avr/compile-only.elf
avr-objcopy -O ihex -R .eeprom build/avr/compile-only.elf build/avr/compile-only.hex
avr-size build/avr/compile-only.elf | tee build/avr/size.txt
python3 scripts/check-size.py
