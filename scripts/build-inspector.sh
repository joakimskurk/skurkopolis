#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
cc -std=c11 -O2 -Wall -Wextra -Werror -I"${SIMAVR_PREFIX:-/usr}/include/simavr" sim/inspect_cpu.c sim/bus_trace.c sim/response_fixture.c sim/spi_timing.c virtual/response_protocol.c -L"${SIMAVR_PREFIX:-/usr}/lib/$(cc -dumpmachine)" -lsimavr -o build/cpu_inspector
