#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
CXX=${CXX:-g++}
FLAGS="-std=c++11 -Wall -Wextra -Werror -pedantic -fno-exceptions -fno-rtti -Icore"
$CXX $FLAGS core/sequencer.cpp tests/core_test.cpp -o build/core_tests
./build/core_tests
$CXX $FLAGS -Ivirtual virtual/synthetic_peripherals.cpp tests/peripheral_contract_test.cpp -o build/peripheral_contract_tests
./build/peripheral_contract_tests
cc -std=c11 -Wall -Wextra -Werror -pedantic -Ivirtual virtual/response_protocol.c tests/response_protocol_test.c -o build/response_protocol_tests
./build/response_protocol_tests
python3 scripts/validate-hardware-spec.py
$CXX $FLAGS core/sequencer.cpp host/trace.cpp -o build/metro_trace
python3 -m unittest discover -s tests -p 'test_*.py' -v
