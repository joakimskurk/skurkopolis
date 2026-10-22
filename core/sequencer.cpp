#include "sequencer.h"
namespace metro {
bool valid(const Phrase& p) {
 if (p.count < 1 || p.count > 8) return false;
 for (uint8_t i=0;i<8;++i) {
  const Stage& s=p.stages[i];
  if(s.note>127 || s.pulses<1 || s.pulses>8 || s.ratchet.count<1 || s.ratchet.count>4) return false;
 }
 uint8_t expected=0;
 for(uint8_t i=0;i<p.count;++i) {
  const Segment& s=p.segments[i];
  if(s.first!=expected || s.last<s.first || s.last>=8 || s.repeats<1 || s.repeats>8) return false;
  expected=s.last+1;
 }
 return expected==8;
}
Phrase canonical() {
 Phrase p={}; const uint8_t notes[8]={48,50,55,53,57,55,59,60};
 for(uint8_t i=0;i<8;++i) p.stages[i]={notes[i],1,{1},false,false};
 p.count=3; p.segments[0]={0,2,2};p.segments[1]={3,4,2};p.segments[2]={5,7,2};
 return p;
}
Engine::Engine() : phrase_(canonical()), state_{}, playable_(true) {}
bool Engine::configure(const Phrase& p) {
 if(!valid(p)) return false;
 phrase_=p; playable_=false;
 for(uint8_t i=0;i<8;++i) if(!p.stages[i].skip) playable_=true;
 reset(); return true;
}
void Engine::reset(){state_={0,0,0,0,0};}
void Engine::advanceStage(){
 const Segment& s=phrase_.segments[state_.segment];
 state_.pulse=0;
 if(state_.stage<s.last){++state_.stage;return;}
 if(++state_.repeat<s.repeats){state_.stage=s.first;return;}
 state_.repeat=0;
 if(++state_.segment>=phrase_.count){state_.segment=0;++state_.cycle;}
 state_.stage=phrase_.segments[state_.segment].first;
}
bool Engine::next(Pulse& out){
 out={};
 if(!playable_) return false;
 // At most 64 stage visits per phrase: 8 stages * 8 repeats.
 for(uint8_t i=0;i<64 && phrase_.stages[state_.stage].skip;++i) advanceStage();
 const Stage& s=phrase_.stages[state_.stage];
 out.position=state_;out.note=s.note;
 if(!s.rest){
  out.gateCount=s.ratchet.count;
  const uint16_t spacing=ticksPerPulse/s.ratchet.count;
  for(uint8_t i=0;i<out.gateCount;++i) out.gates[i]={static_cast<uint16_t>(i*spacing),static_cast<uint16_t>(spacing/2)};
 }
 if(++state_.pulse>=s.pulses) advanceStage();
 return true;
}
}
