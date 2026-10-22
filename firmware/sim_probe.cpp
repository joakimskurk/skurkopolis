#include "sequencer.h"
// Simulator instrumentation only. No rev010 pin mapping, GPIO or EEPROM writes.
// Volatile byte protocol avoids relying on host/AVR struct layout.
extern "C" {
volatile uint8_t lab_status;
volatile uint8_t lab_input[65];
volatile uint8_t lab_output[26];
}
static metro::Engine engine;
static metro::Phrase phrase;
static metro::Pulse pulse;
static void encode(){
 const auto& s=pulse.position;
 for(uint8_t i=0;i<4;++i)lab_output[i]=uint8_t(s.cycle>>(8*i));
 lab_output[4]=s.segment;lab_output[5]=s.repeat;lab_output[6]=s.stage;lab_output[7]=s.pulse;
 lab_output[8]=pulse.note;lab_output[9]=pulse.gateCount;
 for(uint8_t i=0;i<4;++i){uint8_t k=10+4*i;lab_output[k]=pulse.gates[i].offset;lab_output[k+1]=pulse.gates[i].offset>>8;lab_output[k+2]=pulse.gates[i].duration;lab_output[k+3]=pulse.gates[i].duration>>8;}
}
int main(){
 lab_status=1;
 for(;;){
  if(lab_status==2){
   phrase.count=lab_input[0];
   for(uint8_t i=0;i<8;++i){uint8_t k=1+3*i;phrase.segments[i]={lab_input[k],lab_input[k+1],lab_input[k+2]};}
   for(uint8_t i=0;i<8;++i){uint8_t k=25+5*i;phrase.stages[i]={lab_input[k],lab_input[k+1],{lab_input[k+2]},lab_input[k+3]!=0,lab_input[k+4]!=0};}
   lab_status=engine.configure(phrase)?3:7;
  }
  if(lab_status==4){if(engine.next(pulse)){encode();lab_status=5;}else lab_status=6;}
 }
}
