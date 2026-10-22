#include "sequencer.h"
// Compile-only harness. NO GPIO, timers, EEPROM, pin mapping or hardware support.
// Must not be installed on a module. Observable result retained for size inspection.
volatile uint8_t observedStage;
int main(){metro::Engine engine;metro::Pulse pulse;for(;;){if(engine.next(pulse))observedStage=pulse.position.stage;}}
