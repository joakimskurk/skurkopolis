#pragma once
#include <stdint.h>
namespace metro {
constexpr uint8_t stageCount = 8;
constexpr uint16_t ticksPerPulse = 120; // logical units, not CPU time
struct Ratchet { uint8_t count; };
struct Stage { uint8_t note; uint8_t pulses; Ratchet ratchet; bool skip; bool rest; };
struct Segment { uint8_t first; uint8_t last; uint8_t repeats; };
struct Phrase { Stage stages[8]; Segment segments[8]; uint8_t count; };
struct PhraseState { uint32_t cycle; uint8_t segment, repeat, stage, pulse; };
struct Gate { uint16_t offset, duration; };
struct Pulse { PhraseState position; uint8_t note, gateCount; Gate gates[4]; };
bool valid(const Phrase&);
Phrase canonical();
class Engine {
 public:
  Engine();
  bool configure(const Phrase&); // validate then commit; invalid input preserves state
  void reset(); // next call emits first playable pulse
  bool next(Pulse&); // one logical pulse, bounded work even when all stages skipped
 private:
  Phrase phrase_;
  PhraseState state_;
  bool playable_;
  void advanceStage();
};
} // namespace metro
