# Architecture decision record — M0/M1

## One core, narrow boundaries

`Phrase -> Engine::next(Pulse) -> host trace -> JSON -> browser audio/visuals`.
The core also compiles through the AVR harness. WASM is deferred: a native bridge
already gives one implementation without introducing an unverified Emscripten stack.
No second JavaScript sequencer exists. WebAudio converts precomputed offsets to seconds.

The browser receives one complete phrase (maximum 512 pulses), then repeats this
finite trace. This is sufficient for static M1 settings, not future random evolution,
live external clock or stateful AUX processing. Those require a streaming bridge or
WASM instance retaining core state. Do not add mutation in JavaScript.

## Explicit draft semantics

- Core indexes are zero-based. JSON/UI indexes are one-based.
- Segments form a complete consecutive partition of all eight stages; 1–8 segments.
- Each segment repeats 1–8 times; each stage uses 1–8 pulses and 1–4 ratchets.
- A pulse is 120 logical ticks, divisible by all ratchet counts. Each audition gate
  occupies half a subdivision. No microsecond, CPU-clock or CV accuracy is implied.
- Stage notes are 0–127 integer audition notes, not quantized panel ADC readings.
- Only repeat-style audition gates and rest are implemented. Other gate modes are absent.
- Skipped stages consume no pulses. Empty segments consume no time. All-skipped returns
  false and clears the output. Rest consumes pulses with zero gate events.
- `configure` validates before copying. Failure preserves old configuration and state.
  Success resets to the first stage. `reset` prepares the next pulse; no asynchronous I/O.
- Pulse reports current position, then the engine advances. Repeat increments after
  the last stage's last pulse. Phrase cycle is unsigned 32-bit and wraps modulo 2^32.
- Configuration is a fixed private copy. No dangling external configuration pointers.
- No allocation, recursion, exceptions, RTTI or standard containers in core.

## Deliberate limits

No gate cancellation queue in core yet: `next()` describes a pulse plan, not an ISR
scheduler. No editable state while playing in this milestone. Browser edits stop all
scheduled oscillators. Hidden-tab playback stops; late callbacks do not burst catch up.
Browser timing does not validate AVR timing. Compile-only harness must never be flashed.

## Later boundaries

M2: full baseline behavioral spec, gate/slide/direction/clock behavior and tests.
M3: segment policy integration with those behaviors; current tests are a seed, not a pass.
M4: degree/tetra audition. M5: physical interaction freeze.
M6: verified virtual peripherals and AVR simulator. M8: real binary parity.
HAL will translate semantic requests only after measured wiring evidence.

## v0.2 implemented simulation path

The reference route remains native trace. New route: browser -> Python -> simavr
runner -> compiled AVR ELF -> SRAM mailbox -> JSON trace. The runner does not link the
native musical core. A five-second process timeout plus cycle/geometry bounds protect
the local service. This is not yet the virtual-board/WebSocket design described for M6.
See AVR_SCOPE.md; no MCU model signature substitution or native fallback is performed.

## v0.3 evidence boundary

The virtual-board work now has a hard separation between generic peripheral semantics
and actual rev010 wiring. `virtual/synthetic_peripherals.*` may model datasheet behavior
without any AVR pins. `specs/hardware-map.yaml` may contain fixed MCU pin identities,
but board-facing roles/targets require explicit evidence. `scripts/validate-hardware-spec.py`
enforces this mechanically.

This means the next simulator architecture is intentionally two-stage:

`simavr GPIO/ADC/IRQ <-> verified wiring adapter <-> generic peripheral models`

The middle adapter does not exist yet because there is no verified rev010 map. Do not
skip it by hard-coding plausible connections. Once evidence exists, each wiring entry
should be traceable back to a continuity measurement or passive capture and exercised
by synthetic peripheral tests before original firmware is attached.

## v0.4 evidence intake and wiring preflight

`host/evidence.py` validates map schema 3 against the explicit evidence registry.
All asserted board fields require matching reviewed claims and byte-verified artifacts.
A requested digital subset can produce a wiring plan, but no simulator adapter consumes
it yet. This is preflight, not a connected virtual board. No actual map entry has been
assigned. See EVIDENCE_INTAKE.md for schema/workflow and representational limits.

## v0.5 separate original-CPU inspection path

Strict HEX validation -> explicit padded flash image -> bounded unwired simavr run ->
register-change/PC-sample report. This route needs no mailbox and leaves the existing
custom core trace untouched. It is CLI-only, not original-module playback in the UI.
The board mapping gate is unchanged; original firmware runs with disclosed missing
external responses and synthetic settings. Details in CPU_INSPECTION.md.

## v0.6 passive bus analysis

The optional C callback observer feeds bounded JSON events into the standalone Python
GPIO/SPI decoder. A write-only STLED shadow and direct static-I/O inventory support
analysis. No response model is attached to the CPU. Hypotheses live separately in
`specs/firmware-hypotheses-v137.json`, never in the physical map. See BUS_ANALYSIS.md.
The observer uses simavr1.6 internals and preserves original callbacks; SPI timing
remains the unmodified fixed100us baseline.
