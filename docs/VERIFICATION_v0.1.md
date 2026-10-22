# Verification / gate report — 2026-10-18

## Completed in the delivery environment

- Archive SHA-256 and all 10 internal handoff checksums matched.
- All six PCB photographs visually inspected; evidence inventory included.
- Native C++11 compiled with g++, Wall/Wextra/Werror/pedantic, no RTTI/exceptions.
- Canonical segment sequence passed over multiple phrase cycles.
- Reset, reject-without-mutation, pulse/ratchet separation, invalid ranges,
  overlapping/gapped segments, rest, skipped segments and all-skipped cases passed.
- Independent nested-loop oracle checked 72,576 pulses across pulse counts 1–8,
  ratchets 1–4, repeats 1–8 and two phrase cycles per configuration.
- AddressSanitizer + UndefinedBehaviorSanitizer core test passed with
  ASAN_OPTIONS=detect_leaks=0. LeakSanitizer could not run under the host process
  restrictions; no leak-test pass is claimed. Core itself uses no heap allocations.
- Nine Python bridge/HTTP tests passed: canonical trace, maximum 512-pulse phrase,
  all-skipped response, bounds/type rejection, segments, health, static allowlist,
  invalid/oversized requests and successful real HTTP trace delivery.
- JavaScript syntax checked with node --check.
- Local server launched and responded; native trace endpoint exercised over HTTP.

Host layout observations only: Phrase 65 bytes, Engine 80 bytes, Pulse 28 bytes.
These are NOT AVR static RAM, flash or stack measurements.

## Not run / open gates

- Docker Compose build/start: Docker absent.
- CMake configuration/build: CMake absent.
- AVR build and size-budget script: AVR compiler/binutils absent.
- Browser visual/audio/interaction test: Playwright is installed, Chromium is absent.
  Launch failed before executing any browser assertions. tests/browser.cjs is supplied
  for a later environment. No screenshot or listening verification is claimed.
- WASM, simavr board execution, original firmware and physical hardware: unimplemented.

The Dockerfile runs native tests, CMake tests and AVR compile-only build as build gates.
The native sh scripts/test.sh path is the path actually exercised here.
The compile-only ELF/HEX does not implement rev010 I/O and must never be flashed.

## Milestone status

M0 evidence dossier: COMPLETE for available evidence; readout/mapping remains pending.
M1 lab: IMPLEMENTED CANDIDATE, gate OPEN until Docker/AVR and browser checks run.
M2 manual baseline: NOT PASSED; current audition semantics are only a small subset.
M3 segments: canonical regression seed exists, full integration gate NOT PASSED.
M4 onward: NOT STARTED.

## Next acceptance session

1. Run docker compose up --build; retain complete output if the build fails.
2. Check http://localhost:8080, play canonical phrase and test pulses/ratchets separately.
3. Verify 390px mobile and desktop layout; optional node tests/browser.cjs requires
   Playwright and its Chromium installation plus a running local lab.
4. Retrieve AVR size log from the container: docker compose exec lab cat build/avr/size.txt.
5. Record Docker/CMake/compiler versions, then pin base image/package versions.
6. Close M1 only on actual success; proceed to M2 behavior and timing tests.

Conversation length: this milestone fits in the current chat. A complete next-chat
prompt and original handoff are nevertheless included to preserve continuity.
