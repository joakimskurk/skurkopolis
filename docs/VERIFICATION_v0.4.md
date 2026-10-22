# v0.4.0 verification, 2026-10-18

## Scope and intake

The user attached v0.2 for continuity. During this session a newer v0.3 package was
identified and materialized. Its entire SHA-256 manifest matched before edits.
v0.4 is based on v0.3, not a separate branch from v0.2. The earlier v0.2 native tests
also passed during initial reading. All supplied PCB photos were inspected.

This milestone implements evidence intake, strict review/claim validation and digital
wiring-plan preflight. It does not implement a simavr GPIO adapter or read hardware.

## Fresh results in this environment

- Existing C++ core: 72,576 oracle pulses plus canonical/reset/skip/rest checks passed.
- Existing generic peripheral C++ tests passed, without changes to those models.
- New evidence tests: 23 passed. They cover blank/incomplete map handling, a reviewed
  synthetic subset, invented references, pending evidence, artifact tampering/deletion,
  wrong pin/board, unsupported fields, conflicting reviewed claims, confined paths and
  symlink escapes, duplicate ids/JSON keys, fixed pin identity, unsupported clock and
  signature claims, special-pin/analog rejection, ambiguous roles, read-only source
  copying, duplicate/destination protection, writer locking, review fields/timezones,
  optimized Python (-O) guard behavior and blocked CLI exit codes.
- Full Python discovery: 33 tests total, 32 passed and 1 AVR endpoint test skipped.
- Hardware validator passed on the actual blank map: 0 assigned pins, 0 reviewed records.
- JavaScript syntax check passed. No browser interaction/audio result is claimed.
- AVR artifacts and musical core were byte-compared against v0.3 and are unchanged.

`artifacts/evidence-status.json` records current map/registry hashes and readiness.
`artifacts/evidence-verification.json` records test scope. `artifacts/v0.4-tests.txt`
contains the actual test output. Synthetic fixtures exist only in temporary test roots;
the real evidence registry has no invented measurement records.

## Existing evidence and open gates

v0.2's 131 simavr runs / 16,292 matching pulses, 1,530 flash bytes and 275 static SRAM
bytes are retained historical results. AVR GCC and simavr are absent in this environment,
so no fresh AVR build/run is claimed. CMake and Docker are also absent. The prior v0.3
CMake result remains historical; Docker and browser gates are still open.

- M0 evidence intake tooling: implemented and tested; physical measurements pending.
- M1 native/HTTP: passed. CMake not rerun; Docker/browser still open.
- M2 original behavior and M3 full integration: not passed.
- M6 generic component contracts: inherited tests pass, not full serial/timing emulation.
- M6 reviewed mapping preflight: passed software tests; actual board remains blocked.
- M6 simavr board adapter: not implemented.
- M7 original firmware: not started.

A ready requested wiring subset is not a whole-board qualification. Hashes and named
reviewers cannot establish whether a measurement is truthful; this remains a human
engineering review. Evidence ingestion uses locking plus atomic registry replacement,
not full multi-file crash durability. Shared bus fanout and hardwired ties need a richer
netlist schema before integration. Private evidence is excluded from distributed builds;
missing referenced evidence deliberately causes validation to fail.

## Next step and chat length

Obtain real read-only board data per MAPPING_WORKSHEET.md. Start with programmer model,
power arrangement and ICSP orientation, then identity/fuses and observed connections.
Register and review artifacts before implementing any board-specific adapter.
Software alternatives should target concrete unclosed tests, not invent wiring or
inflate musical features. This chat can continue for a focused next step; the complete
package includes an updated handoff for a fresh chat before a large simulator milestone.
