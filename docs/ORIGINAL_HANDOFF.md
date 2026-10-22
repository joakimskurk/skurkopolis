# METROPOLIS FIRMWARE LAB — MASTER HANDOFF
**Date:** 2026-10-18  
**Status:** concept/architecture phase complete; implementation has NOT started yet.  
**Purpose:** Continue in a new chat without losing any architectural, hardware, firmware, UX, or musical-design context.

---

# 0. EXECUTIVE SUMMARY

The project is to build a replacement/custom firmware ecosystem for an original Intellijel Metropolis, specifically the user's **METROPOLIS Main rev010** board, with the goal of preserving the immediate, hands-on strengths of the original sequencer while making it **substantially more melodic and compositional**.

The core musical direction is NOT “clone Metropolix on old hardware.” The direction is:

> Preserve the recognisable Metropolis sequencing model, then add a deep melodic/tonal layer inspired by the user's own SkurkyMello ideas and by the conceptual approach of Cycle Instruments Tetrachords.

The two most important new features defined so far are:

1. **Tetrachords-inspired melodic/interval lane using the 8 pitch sliders.**
   - Instead of entering intervals through button presses, the eight physical sliders become a direct gestural editor for melodic degrees/interval transforms.
   - This should be scale/tetrachord aware, not merely chromatic transposition.
   - It should turn Metropolis into a much more melodic instrument while remaining playable and immediate.

2. **Segmented phrase playback from SkurkyMello.**
   - The 8-stage sequence can be split into consecutive sub-sequences/segments.
   - Example explicitly requested by the user:
     - stages **1–3 play twice**
     - then stages **4–5 play twice**
     - then stages **6–8 play twice**
   - Therefore the event order becomes:
     `1 2 3 | 1 2 3 | 4 5 | 4 5 | 6 7 8 | 6 7 8`
   - This must be conceptually separate from stage pulse-count and ratchet.

The development strategy is to first build a **Docker-packaged “Metropolis Firmware Lab”** that acts as a safe sandbox. The lab should eventually support:
- a high-level reference model of Metropolis behavior,
- the custom sequencer core,
- browser/WebAudio/MIDI auditioning,
- a virtual Metropolis front panel,
- AVR firmware build,
- simavr execution of the actual compiled `.hex`,
- eventually local loading of the original Intellijel firmware `.hex` for A/B behavior validation,
- virtualized board peripherals,
- timing/debug inspection.

The target architecture is deliberately designed so that the musical sequencer logic is NOT duplicated in JavaScript and AVR C. The same core logic should be reusable across:
- native host tests,
- WebAssembly/reference sandbox,
- ATmega328 firmware.

---

# 1. USER INTENT / PRODUCT DIRECTION

The user owns an original Intellijel Metropolis and wants to explore replacing its firmware with a much more musically advanced custom firmware.

The desired result should:
- still feel like Metropolis,
- preserve fast performance-oriented interaction,
- avoid menu hell,
- make the existing 8-stage physical panel much deeper rather than simply adding feature count,
- focus strongly on melodic composition,
- incorporate selected SkurkyMello ideas,
- incorporate Tetrachords-inspired tonal/interval thinking,
- remain monophonic in the first serious version because the original Metropolis has one pitch-CV lane,
- treat the limited AVR hardware as a creative constraint rather than trying to imitate a modern ARM module.

Do NOT drift toward:
- a generic “everything sequencer,”
- a Metropolix clone,
- a huge menu system,
- polyphony/chord generation before the monophonic engine is excellent,
- rewriting every SkurkyMello feature onto the module,
- fragile direct experimentation on the original MCU before backups and board understanding exist.

A useful product-design sentence already established in the conversation:

> “Do not add as many features as possible. Make the existing eight stages musically deeper.”

Another useful summary:

> “Metropolis, but each stage describes melodic intention rather than only a voltage.”

---

# 2. VERIFIED HARDWARE FACTS FROM THE USER'S PHOTOS

## 2.1 Main board revision
Silkscreen on the user's PCB clearly reads:

`Intellijel Designs Inc.`
`METROPOLIS Main rev010`

Therefore all hardware mapping work MUST be scoped to **rev010** first.

Do not assume other Metropolis board revisions use exactly the same wiring or supporting ICs.

## 2.2 Main MCU
The main socketed MCU marked IC12 is visibly:

`ATMEGA328-PU`

Important:
- This is **ATmega328**, not ATmega328P.
- It is a 28-pin PDIP package and is socketed.
- The socketed arrangement is extremely useful for safe replacement/development.
- Do not casually substitute a 328P without understanding device signatures, fuse behavior and programmer expectations.

Useful architectural facts for ATmega328:
- 32 KB flash
- 2 KB SRAM
- 1 KB EEPROM
- AVR 8-bit architecture
- timers, ADC, SPI, TWI/I²C, UART and GPIO suitable for this application

The exact clock source/fuses are NOT yet known and must be read from the original device.

## 2.3 ICSP
The PCB includes a clearly labeled **ICSP** header adjacent to the MCU.

This supports the planned workflow:
- read device signature,
- read fuse bits,
- read lock bits,
- back up EEPROM,
- read FLASH if lock bits permit,
- program a replacement chip later.

IMPORTANT: do not perform chip erase or write operations on the original MCU during the discovery phase.

## 2.4 Display/keyscan driver
A photographed support IC was identified in the prior discussion as an **STLED316S-family** device.

This is significant because the STLED316S family combines LED/display driving and keyscan functionality and communicates over a small serial interface. This plausibly explains how the Metropolis panel can expose many LEDs/buttons while using relatively few MCU pins.

Treat the precise board role as “high confidence but still to be verified in the hardware map.”

## 2.5 Analog multiplexing
At least one photographed IC was identified as a **74HC4051D**-type 8-to-1 analog multiplexer.

This is consistent with reading groups of sliders/pots into a limited number of AVR ADC inputs.

Again:
- component identification is high-confidence,
- exact signal routing is NOT yet mapped.

## 2.6 Other analog/support ICs
Multiple op-amp/logic/analog ICs are visible on the PCB, but not all have been definitively identified and mapped.

Do NOT assume:
- exact DAC architecture,
- exact CV output resolution,
- exact pitch generation path,
- exact slide circuit,
- exact AUX conditioning,
- exact gate driver topology,
until traced or measured.

This matters especially for any promise of microtonal precision.

---

# 3. ORIGINAL METROPOLIS — DOCUMENTED BEHAVIOR BASELINE

The original Metropolis manual used in planning is the Intellijel **Metropolis manual v1.30**.

The original module has eight stages with core per-stage concepts including:
- pitch
- pulse count
- gate mode
- slide
- skip
- ratchet

It also supports sequence-direction/mode concepts including:
- Forward
- Reverse
- Ping-Pong
- Brownian
- Random
- fixed-pulse variants / pulse-based sequence modes

Other documented behavior includes:
- internal and external clocking
- clock division
- swing
- scale/root quantization
- two AUX modulation inputs
- preset save/load in EEPROM
- use of the 8 stage-related buttons for shortcuts/secondary functions

The manual should be treated as a **behavioral specification source**, not merely as reference reading.

The public firmware currently discussed is **1.37**, whereas the manual is v1.30. Therefore:
- first build a manual-conformant 1.30 reference model,
- then compare against actual 1.37 behavior where possible,
- document all observed differences,
- never silently assume 1.37 == manual 1.30.

Official resources previously referenced in the discussion:
- Metropolis manual:
  https://intellijel.com/downloads/manuals/metropolis_manual_1.30_2020.05.12.pdf
- Intellijel legacy firmware/support:
  https://intellijel.com/support/
- Intellijel legacy updater/firmware guidance:
  https://intellijel.com/support/firmware-windows/

---

# 4. CLEAN-ROOM / ORIGINAL FIRMWARE STRATEGY

The project should NOT begin by attempting to “decompile and edit” the original Intellijel firmware.

Preferred strategy:
1. Treat the original unit and firmware as the behavioral reference.
2. Build a clean replacement firmware from scratch.
3. Use the original firmware only locally for:
   - behavior comparison,
   - hardware interaction discovery where appropriate,
   - timing/reference testing.
4. Do not redistribute Intellijel firmware inside the custom project or Docker image.
5. If an official `.hex` can be obtained from Intellijel's updater package, keep it in a gitignored local directory such as:
   `firmware-local/ORIGINAL_METROPOLIS_1_37.hex`
6. If the original MCU is read-protected, do not attempt to bypass protection.
7. The original physical ATmega should be preserved as the fallback “factory recovery” device whenever practical.

The ideal safe arrangement later:
- original socketed ATMEGA328-PU stored untouched,
- one or more replacement ATMEGA328-PU devices used for development/custom firmware.

---

# 5. BACKUP / DISCOVERY PROCEDURE BEFORE ANY HARDWARE WRITING

Before modifying real hardware, perform a read-only discovery session via ICSP.

Record:
- device signature
- low fuse
- high fuse
- extended fuse
- lock bits
- calibration data if relevant/readable
- EEPROM dump
- FLASH dump if allowed

For every dump:
- retain raw binary/HEX,
- record tool command,
- compute SHA-256,
- record date,
- record programmer model,
- record whether the module was externally powered.

IMPORTANT power rule:
Do not let the ISP programmer and Eurorack supply fight each other by both powering the target simultaneously unless the exact programmer arrangement is understood and intentionally configured.

No write/erase command is allowed during M0/M1 discovery.

---

# 6. CENTRAL SOFTWARE ARCHITECTURE

The core architectural rule is:

> The musical sequencer engine must be hardware-independent.

Do not build:
- one JavaScript sequencer,
- one unrelated AVR sequencer,
- one unrelated emulator model.

Instead build one deterministic core and multiple backends.

Target conceptual architecture:

```text
                       METROPOLIS CORE
                hardware-independent C/C++
                         /    |    \
                        /     |     \
                  Native     WASM     AVR
                   tests      |        |
                              |      HAL_AVR
                              |        |
                         Web Lab     rev010
```

Parallel simulation path:

```text
Original 1.37 HEX or Custom AVR HEX
                |
              simavr
                |
      Virtual rev010 peripherals
                |
          simulator bridge
                |
             Web UI
```

## 6.1 Metropolis Core responsibilities
The core can know about:
- stages
- pulse count
- ratchets
- skip
- slide semantic state
- sequence direction
- segment structure
- phrase state
- scale/root
- tetrachord/degree logic
- melodic transformation
- deterministic random state
- clock-event semantics
- preset/state representation

The core MUST NOT know:
- actual AVR pin numbers
- STLED serial protocol
- ADC channel numbers
- mux address pins
- CV output electronics
- exact LED wiring
- specific interrupt vectors

## 6.2 Hardware abstraction layer
The firmware side should expose narrow abstractions such as:

```cpp
uint16_t readPitchSlider(uint8_t stage);
uint8_t  readPulseSlider(uint8_t stage);
GateMode readGateMode(uint8_t stage);

bool     readStageButton(uint8_t stage);
uint16_t readAuxA();
uint16_t readAuxB();

void setStageLed(uint8_t stage, bool on);
void setDisplay(...);
void setGate(bool high);
void setSync(bool high);
void setPitchRaw(uint16_t value);
```

The core should emit semantic requests. The HAL translates them into real board I/O.

Potential backends:
- `HardwareBackend_Host`
- `HardwareBackend_WASM`
- `HardwareBackend_Sim`
- `HardwareBackend_Rev010`

---

# 7. DOCKER “METROPOLIS FIRMWARE LAB”

The requested sandbox should be delivered as a Docker-packaged local project.

Desired UX:
```bash
docker compose up
```

Then open:
```text
http://localhost:8080
```

## 7.1 Recommended toolchain inside Docker
At minimum:
- avr-gcc
- avr-libc
- binutils-avr
- avrdude
- simavr
- cmake
- ninja or make
- Python
- Node.js
- Vite or similarly lightweight web dev tooling
- Emscripten if the C++ core is compiled to WASM
- test runner for host-side deterministic tests

## 7.2 Suggested project layout

```text
metropolis-firmware-lab/
│
├── compose.yaml
├── Dockerfile
├── CMakeLists.txt
│
├── core/
│   ├── sequencer/
│   ├── timing/
│   ├── segments/
│   ├── tonal/
│   ├── random/
│   ├── state/
│   └── include/
│
├── firmware/
│   ├── main.cpp
│   ├── hal_avr.cpp
│   ├── panel_scan.cpp
│   ├── output.cpp
│   ├── eeprom.cpp
│   └── board_rev010/
│
├── sim/
│   ├── rev010_board/
│   ├── stled316/
│   ├── analog_mux/
│   ├── analog_inputs/
│   ├── cv_outputs/
│   ├── clock_reset/
│   └── bridge/
│
├── web/
│   ├── panel/
│   ├── debug/
│   ├── midi/
│   ├── audio/
│   └── transport/
│
├── tests/
│   ├── manual/
│   ├── timing/
│   ├── segment/
│   ├── tonal/
│   ├── regression/
│   └── golden/
│
├── specs/
│   ├── hardware-map.yaml
│   ├── behavior-v130.yaml
│   ├── behavior-v137-notes.yaml
│   ├── preset-format.md
│   └── ui-map.md
│
├── scripts/
│   ├── build-avr.sh
│   ├── build-wasm.sh
│   ├── test.sh
│   ├── inspect-size.sh
│   └── hash-artifacts.sh
│
└── firmware-local/
    └── .gitignore
```

## 7.3 Runtime modes in the Web Lab
Eventually the UI should expose three engines:

```text
ENGINE
[ Reference Model ]
[ Custom AVR Firmware ]
[ Original Metropolis ]
```

### Reference Model
Runs the hardware-independent core directly/through WASM.
Purpose:
- musical feature design,
- fast iteration,
- UI testing,
- deterministic tests.

### Custom AVR Firmware
Runs the actual custom compiled `.hex` through simavr plus virtual rev010 peripherals.
Purpose:
- prove the same firmware binary intended for the physical module behaves correctly.

### Original Metropolis
Loads a user-supplied local original firmware `.hex` through the same virtual rev010 board.
Purpose:
- A/B behavior comparison,
- reverse engineering of behavior,
- regression reference.

Do NOT bundle original Intellijel firmware.

---

# 8. SIMULATOR / BROWSER BRIDGE

Because simavr is a native process rather than ordinary browser JavaScript, the recommended design is:

```text
Browser UI
   |
WebSocket
   |
Simulator bridge service
   |
simavr + virtual rev010 peripherals
```

The bridge should expose structured events such as:

```json
{
  "type": "state",
  "stage": 3,
  "segment": 1,
  "segmentRepeat": 2,
  "pulse": 1,
  "gate": true,
  "pitchRaw": 1234
}
```

And accept control messages such as:
- slider position changes
- button presses
- rotary control changes
- clock edges
- reset
- AUX voltage changes
- load/reset firmware

The browser does NOT need to know AVR register details.

---

# 9. WEB LAB FRONT PANEL

The Web Lab should visually follow the physical Metropolis closely enough that interaction translates naturally to the real module.

Minimum v0.1 panel:
- 8 pitch sliders
- 8 pulse-count sliders
- gate-mode controls
- stage LEDs
- SLIDE/SKIP button states
- ratchet state
- encoder/buttons used by the real module
- clock/reset
- AUX A/B controls
- display
- BPM/clock source
- pitch/gate monitor

Additionally, developer-only areas:
- event inspector
- phrase/segment inspector
- tonal-resolution inspector
- raw slider values
- state-machine view
- deterministic seed
- CV value
- gate waveform
- timing diagnostics

Useful debug example:

```text
CLOCK           124 BPM
STAGE           3
PULSE           1 / 4
RATCHET         2 / 3
SEGMENT         A
SEGMENT REPEAT  2 / 2

BASE DEGREE     4
MELODY OFFSET  +2
RESOLVED DEGREE 6
NOTE            Bb3
PITCH RAW       0x07A1
GATE            HIGH
```

Web Lab auditioning should support:
- simple internal WebAudio synth,
- WebMIDI output if available,
- optional MIDI note mapping from pitch/gate for musical evaluation.

The point is to hear whether the new engine is musically useful before flashing hardware.

---

# 10. MANUAL → EXECUTABLE BEHAVIOR SPEC

Do not merely “match the manual by eye.”

Translate original Metropolis behaviors into automated tests.

Example pulse count test:

```text
Given:
  direction = Forward
  stage 1 pulseCount = 3

Clock 1 -> stage 1, pulse 1
Clock 2 -> stage 1, pulse 2
Clock 3 -> stage 1, pulse 3
Clock 4 -> stage 2, pulse 1
```

Skip test:

```text
stage 3 = SKIP

expected stage sequence:
1 -> 2 -> 4
```

Ratchet test:
- a pulse can create 1/2/3/4 sub-events according to the original semantics,
- exact gate timing must be measured/validated.

Direction tests:
- Forward
- Reverse
- Ping-Pong
- Brownian
- Random
- any fixed-pulse/alternate traversal mode documented by the original manual

Also test:
- reset
- internal clock
- external clock
- divisions
- swing
- scale/root behavior
- AUX mappings
- save/load behavior
- stage length/skip interactions
- slide interactions
- single/repeat/hold/rest gate semantics

This test suite becomes the original-behavior compatibility layer.

---

# 11. THE MOST IMPORTANT NEW FEATURE: SEGMENT ENGINE

The user explicitly wants the SkurkyMello-style ability to divide the sequence into smaller consecutive phrases and repeat each phrase before moving on.

Canonical example:

```text
SEG A: stages 1–3, repeat 2
SEG B: stages 4–5, repeat 2
SEG C: stages 6–8, repeat 2
```

Playback:

```text
1 2 3
1 2 3
4 5
4 5
6 7 8
6 7 8
```

This is NOT equivalent to pulse count.

Pulse count means:
> remain on an individual stage for N clocks.

Segment repeat means:
> replay a sequence of stages as a musical phrase N times.

This distinction is non-negotiable.

## 11.1 Core timing hierarchy
Use this semantic hierarchy:

```text
PHRASE
  └── SEGMENT
       └── STAGE
            └── PULSE
                 └── RATCHET
```

Do not collapse these concepts into one index.

## 11.2 Initial segment structure
A segment can start very small:

```cpp
struct Segment {
    uint8_t startStage;
    uint8_t endStage;
    uint8_t repeats;
    uint8_t direction;
    uint8_t flags;
};
```

Exact packing can be optimized later.

Initial release scope:
- consecutive non-overlapping segments
- start/end boundaries
- repeat count
- default forward traversal

Later possibilities:
- direction per segment
- alternate traversal
- transpose per segment
- mutation/evolve amount
- probability

Do NOT put all later ideas into v0.1.

## 11.3 Candidate hardware UX
Current promising concept:
- use the existing STAGES context/button plus the eight stage buttons to enter a segment editor,
- define segment boundaries with stage buttons,
- encoder adjusts repeat count,
- display gives concise feedback.

Illustrative idea:
```text
SEG
A 1-3 r2
B 4-5 r2
C 6-8 r2
```

This is NOT final. It must be played in the Web Lab before locking it.

---

# 12. TETRACHORDS-INSPIRED MELODIC ENGINE

The user specifically wants to imagine **one Tetrachords-like channel**, but instead of entering intervals through button presses, **the eight physical Metropolis sliders are used directly**.

This is the main melodic innovation.

The inspiration is conceptual:
- scale degrees / interval relationships,
- tonal structures,
- melodic transformation,
- meaningful note relationships,
not copying another module's exact UI or implementation.

## 12.1 Core design principle
The pitch sliders should be capable of representing **musical intention** rather than only absolute voltage.

Potential pitch engines:

```text
LEGACY
DEGREE
TETRA
```

### LEGACY
Preserve original Metropolis-style pitch behavior/quantization.

### DEGREE
Slider selects or offsets a scale degree.

Example conceptual values:
```text
-7 -6 ... -1 0 +1 ... +7
```

But values refer to **scale degrees**, not semitones.

### TETRA
Slider addresses a tetrachord/tonal structure:
- position inside lower/upper tetrachord,
- degree transforms,
- configured tonal topology.

The exact model is deliberately not frozen yet.

## 12.2 Two promising ways to use the eight sliders
These need to be tested musically in Web Lab.

### Option A — Degree lane
Each stage's slider directly selects a note/degree in the active tonal system.

### Option B — Melodic transform lane
The normal/base Metropolis pitch exists conceptually, while the slider layer stores offsets such as:

```text
0  +2  -1  +1  +3  0  -2  +1
```

where `+2` means “two valid scale degrees upward,” not “two semitones.”

This lets a base sequence be transformed while retaining its original contour/identity.

Do NOT decide A vs B purely theoretically; prototype and listen.

## 12.3 Tonal data representation
Keep tonal structures compact in PROGMEM/flash.

Possible internal model:
```text
root
scale/tetrachord id
degree table
optional octave behavior
optional transform policy
```

Because the AVR does not need audio DSP, tonal lookup tables are cheap.

## 12.4 Advanced tonal ideas — future, not v0.1
Potential later features:
- tonal gravity
- phrase-aware melodic mutation
- controlled tension
- directional voice leading
- approach tones
- scale/tetrachord modulation
- AUX modulation of tension/mutation
- per-segment transposition
- evolution between segment repetitions

These are attractive but should not delay:
1. a solid segment engine,
2. a musically useful degree/tetra lane,
3. correct original Metropolis timing.

---

# 13. SOFT TAKEOVER / PICKUP

Multiple logical slider layers create a physical-control mismatch:
- stored logical value may differ from the current physical slider position.

Original Metropolis behavior can “jump” when a saved value is overwritten by moving a slider.

For the custom layered firmware, that may be too destructive.

Plan to prototype **soft takeover/pickup**:

```text
stored logical value = +3
physical slider position = -4

movement ignored until physical position approaches stored value
then:
PICKUP
physical slider takes control
```

Feedback can use:
- display,
- LED state,
- direction hint.

This interaction must be prototyped in Web Lab before implementation on hardware.

---

# 14. AVR MEMORY / IMPLEMENTATION DISCIPLINE

ATmega328 gives only:
- 32 KB flash
- 2 KB SRAM
- 1 KB EEPROM

Treat SRAM as the scarce resource.

Firmware rules:
- no runtime `malloc`
- no runtime `new`
- no dynamic STL containers
- no exceptions
- no RTTI
- no recursion
- fixed-size arrays
- compact enums/bitfields where appropriate
- PROGMEM for lookup tables and text
- fixed-point arithmetic where practical
- deterministic random PRNG
- avoid large debug strings in production AVR builds

Suggested early budget goals:
```text
FLASH target:       < 26 KB
static/global SRAM: < 1.2 KB
EEPROM usage:       < ~900 B
```

These are design targets, not hard laws, but preserve stack/headroom.

Automate size inspection after every AVR build.

---

# 15. CLOCK / REALTIME ARCHITECTURE

Do not build the firmware around one giant Arduino-style `loop()`.

External clock ISR should do minimal work:
- detect edge,
- timestamp / increment event counter,
- enqueue/flag work.

A timer-driven scheduling layer should handle:
- ratchet subdivision,
- gate timing,
- pulse timing,
- glide timing hooks if required.

Main loop can handle:
- panel scan
- display updates
- state transitions
- non-critical menu logic
- AUX scanning
- save/load commands

Goal:
display scanning or UI activity must never cause late ratchets or sloppy gates.

simavr should be used for timing validation and, where useful, VCD traces showing:
- incoming clock
- stage transition
- pitch output change
- gate high/low
- ratchet edges
- reset behavior

---

# 16. EEPROM / PRESET FORMAT

The replacement firmware should own a versioned preset/state format from day one.

Suggested structure:
```text
MAGIC
FORMAT_VERSION
CRC
global settings
legacy stage data
segment definitions
tonal engine config
melodic lane data
future reserved bytes
```

Design requirements:
- versioned migrations
- corruption detection
- fixed-size or bounded structure
- no constant autosaving
- write only on explicit save unless a later robust wear-managed scheme is intentionally designed

Original Metropolis offers multiple preset slots; preserving a similar immediate save/load concept is desirable.

---

# 17. HARDWARE MAP SPECIFICATION

A formal `hardware-map.yaml` should be created.

For every MCU pin and discovered signal:

```yaml
PB0:
  direction: output
  role: unknown
  target_ic: unknown
  target_pin: unknown
  active_level: unknown
  confidence: low
  evidence:
    - pcb_trace
```

Track:
- AVR pin
- port bit
- direction
- connected component
- component pin
- signal type
- active high/low
- pull-up/pull-down
- analog/digital
- interrupt relevance
- confidence level
- evidence source
- verification status

Do not write code against guessed pin mappings without marking uncertainty.

---

# 18. REAL HARDWARE BRING-UP ORDER

Real-hardware custom firmware comes late.

Use a replacement ATMEGA328-PU, not the preserved original, when practical.

Recommended bring-up sequence:

## Firmware 0.0.1 — board sanity
- boot
- display test
- all stage LEDs test
- button/keyscan monitor
- slider raw-value monitor

## Firmware 0.0.2 — transport inputs
- external clock
- reset
- stage LED traversal

## Firmware 0.0.3 — digital outputs
- gate
- sync

## Firmware 0.0.4 — pitch path
- pitch output
- calibration behavior
- quantization verification

## Firmware 0.0.5 — analog/performance features
- slide
- AUX A/B
- remaining controls

## Firmware 0.1 — musical core
- baseline Metropolis behavior
- segment engine
- first degree/tetra mode

Only after lower layers pass should the complete musical firmware run on hardware.

---

# 19. PROJECT MILESTONES / GATES

## M0 — Evidence and dossier
Deliver:
- photo inventory
- board revision record
- MCU identification
- support IC observations
- source/manual index
- read-only backup procedure
- unknowns list

Gate:
No hardware writes.

## M1 — Docker skeleton
Deliver:
- Dockerfile
- compose.yaml
- CMake/toolchain
- host test target
- AVR build target
- web dev target
- CI-like local test script

Gate:
`docker compose up` works reproducibly.

## M2 — Original behavior reference model
Deliver:
- 8-stage engine
- pulse count
- skip
- ratchet
- gate semantics
- forward/reverse/ping-pong/etc.
- manual-derived tests

Gate:
Manual behavior tests green.

## M3 — Segment engine
Deliver:
- Phrase > Segment > Stage > Pulse > Ratchet hierarchy
- exact requested 3/2/3 segmentation case
- editor prototype in Web Lab
- unit tests

Gate:
Segment repeat does not corrupt pulse/ratchet semantics.

## M4 — Melodic/tetrachord sandbox
Deliver:
- LEGACY/DEGREE/TETRA experiments
- scale/tetrachord structures
- 8-slider melodic lane
- WebAudio/MIDI audition
- debug inspector

Gate:
User validates that the idea is musically compelling before firmware complexity increases.

## M5 — UI/interaction freeze v1
Deliver:
- exact physical-panel control map for segment editing
- exact pitch-layer switching behavior
- pickup/soft-takeover behavior
- display vocabulary

Gate:
No menu hell; user can operate core new functions quickly.

## M6 — simavr + virtual rev010 board
Deliver:
- ATmega328 target
- GPIO/timer/ADC infrastructure
- virtual key/display driver
- virtual analog mux
- virtual clock/reset
- browser bridge

Gate:
A basic custom AVR test HEX drives virtual hardware correctly.

## M7 — Original firmware local execution, if obtainable
Deliver:
- user-supplied original HEX loading
- behavior A/B mode
- notes on 1.30 manual vs 1.37 behavior

Gate:
No redistribution of original firmware.

## M8 — Custom AVR firmware parity
Deliver:
- custom `.hex`
- same logical test vectors as host core
- timing tests
- code size report

Gate:
Reference engine and AVR firmware agree on deterministic scenarios.

## M9 — Replacement MCU hardware test
Deliver:
- test firmware on spare ATmega
- display/LED/input validation

Gate:
Original MCU remains recoverable/unmodified.

## M10 — CV/gate/clock validation
Deliver:
- measured timing
- pitch accuracy
- reset behavior
- AUX range
- calibration notes

Gate:
No musical release until output behavior is trusted.

## M11 — First musical firmware
Deliver:
- original-style core behavior
- segment engine
- first approved tonal lane
- save/load

## M12 — polish/release
Deliver:
- robust firmware updater instructions
- backup/recovery documentation
- preset migrations
- end-user manual
- packaged `.hex`
- source/build reproducibility

---

# 20. WHAT IS ALREADY DECIDED VS NOT DECIDED

## DECIDED / STRONGLY AGREED
- Target board first: Metropolis Main rev010.
- MCU: ATMEGA328-PU.
- Preserve original MCU as recovery where possible.
- Clean-room replacement firmware is preferable to editing a decompiled binary.
- Docker Firmware Lab is the development path.
- simavr/native AVR simulation is preferred for real firmware execution.
- High-level musical core should be hardware-independent.
- Segment engine is a core feature.
- The exact requested segment use case is `[1-3]x2 -> [4-5]x2 -> [6-8]x2`.
- Tetrachords-inspired melodic/interval lane is a core feature.
- Eight sliders should directly edit the melodic/interval concept.
- First serious release remains monophonic.
- Original firmware may be loaded locally for testing but not bundled/distributed.
- Manual behavior should become automated tests.
- Real hardware flashing comes after sandbox and mapping work.

## NOT YET DECIDED
- Exact DEGREE vs OFFSET vs hybrid behavior of the melodic lane.
- Exact physical gesture/button to enter the tonal layer.
- Exact segment-editor interaction.
- Exact maximum number of segments.
- Whether segment direction is included in first firmware.
- Exact pitch CV/DAC architecture and achievable microtonal resolution.
- Exact pin map.
- Exact STLED/keyscan routing.
- Exact mux topology.
- Exact fuse/clock configuration.
- Exact differences between firmware 1.30 documentation and firmware 1.37.
- Exact original firmware HEX acquisition path.
- Exact front-end framework.
- Exact host test framework.
- Exact programmer hardware the user will use.

---

# 21. IMPORTANT PITFALLS TO AVOID

1. Do not use ATmega328P assumptions just because Arduino examples are common.
2. Do not overwrite the original MCU before reading signature/fuses/locks/EEPROM.
3. Do not perform chip erase casually.
4. Do not assume every photographed IC role without trace verification.
5. Do not promise microtonal precision before the pitch-output architecture is known.
6. Do not create two unrelated sequencer implementations in JS and AVR.
7. Do not implement too many musical features before segment + melodic lane are validated.
8. Do not let display/UI code disturb clock/gate timing.
9. Do not rely on dynamic allocation on a 2 KB SRAM target.
10. Do not bundle Intellijel firmware.
11. Do not confuse stage pulse repetition with phrase/segment repetition.
12. Do not make the custom firmware dependent on a deep menu system.
13. Do not assume manual v1.30 completely describes firmware v1.37.
14. Do not proceed to physical flash until simulation + board test firmware are trustworthy.

---

# 22. RECOMMENDED IMMEDIATE NEXT STEP IN THE NEW CHAT

The new chat should NOT spend another long turn re-discussing the concept.

Proceed directly to **M0 + M1**:

### Step A — Formalize source/evidence
Create:
- `specs/hardware-map.yaml`
- `specs/behavior-v130.yaml`
- `docs/KNOWN_UNKNOWN.md`
- `docs/HARDWARE_EVIDENCE.md`

Use the attached PCB photos in this handoff package.

### Step B — Build Docker lab skeleton
Create a first working project with:
- Dockerfile
- compose.yaml
- CMake
- host core library
- host tests
- AVR toolchain compile target
- Web Lab placeholder
- scripts

### Step C — Implement the first deterministic core types
Only:
- Stage
- Pulse
- Ratchet
- Segment
- Phrase state

No fancy tonal engine yet.

### Step D — Add canonical segment regression test
Test:
```text
segments:
A 1-3 x2
B 4-5 x2
C 6-8 x2

expected:
1,2,3,1,2,3,4,5,4,5,6,7,8,6,7,8
```

Then test with independent pulse counts and ratchets to prove the hierarchy is correct.

### Step E — Build Web Lab v0.1
Render eight stages and audition the segment engine.

Only after that:
- implement manual-compatible baseline behavior,
- then add DEGREE/TETRA experimental lane.

---

# 23. IDEAL NEXT-CHAT FIRST RESPONSE

The assistant in the next chat should:
1. confirm it has read this handoff,
2. summarize the current gate in 5–10 bullets,
3. state that implementation begins at M0/M1,
4. inspect the included PCB images,
5. create the actual Docker project skeleton,
6. avoid asking the user to re-explain the product idea,
7. preserve the architectural separation and milestone gates in this document.

---

# 24. HANDOFF PACKAGE CONTENTS

This package should contain:
- this master handoff,
- a concise next-chat prompt,
- a source index,
- the user's PCB photos that were available in the current runtime.

The images are evidence/context only; they are not yet a complete schematic.

---

# 25. CONTEXT FROM RELATED USER PROJECTS THAT MATTERS

The user has an existing sequencer project called **SkurkyMello**. The relevant conceptual inheritance here is specifically:
- sequence segmentation,
- looping/repeating slices of the main sequence,
- controlled musical variation,
- the desire for advanced but playable sequencer behavior.

Do NOT import SkurkyMello wholesale.
The current Metropolis project should remain its own instrument.

The user especially values:
- careful architecture,
- phased implementation,
- explicit gates,
- robust handoffs before chats become too long,
- finished usable deliverables rather than vague pseudo-code.

When implementation starts, prefer producing a complete downloadable project/package at each meaningful milestone.

---

# END OF MASTER HANDOFF
