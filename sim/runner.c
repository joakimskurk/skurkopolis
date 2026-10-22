// Executes our instrumented AVR ELF, not original Metropolis firmware.
#define _POSIX_C_SOURCE 200809L
#include <sim_avr.h>
#include <sim_elf.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static avr_t *avr;
static uint16_t lowest_sp;
static int track_stack;
static void fail(const char *s){fprintf(stderr,"sim probe: %s\n",s);exit(2);}
static uint16_t symbol(elf_firmware_t *f,const char *name,unsigned width){
 for(uint32_t i=0;i<f->symbolcount;++i)if(!strcmp(f->symbol[i]->symbol,name)){
  uint32_t a=f->symbol[i]->addr;
  if(a<0x800100u || a+width>0x800000u+avr->ramend+1u)fail("mailbox outside SRAM");
  return (uint16_t)(a-0x800000);
 }
 fail("instrumentation symbol missing; this runner accepts only our probe ELF");return 0;
}
static void wait_status(uint16_t address,uint8_t value){
 uint64_t end=avr->cycle+2000000;
 while(avr->data[address]!=value){
  int state=avr_run(avr);
  if(track_stack){uint16_t sp=avr->data[R_SPL]|(avr->data[R_SPH]<<8);if(sp<lowest_sp)lowest_sp=sp;}
  if(state==cpu_Crashed||state==cpu_Done||avr->cycle>end)fail("crash or cycle budget exceeded");
  if(avr->data[address]==7)fail("firmware rejected configuration");
  if(value==5&&avr->data[address]==6)return;
 }
}
static uint16_t u16(uint16_t a){return avr->data[a]|(avr->data[a+1]<<8);}
int main(int argc,char **argv){
 if(argc!=2)fail("usage: sim_runner build/avr/sim-probe.elf < wire-config.bin");
 // Keep simavr diagnostics off the JSON result channel.
 FILE *output=fdopen(dup(STDOUT_FILENO),"w");if(!output||dup2(STDERR_FILENO,STDOUT_FILENO)<0)fail("output setup");
 uint8_t input[65];if(fread(input,1,65,stdin)!=65||fgetc(stdin)!=EOF)fail("expected 65-byte configuration");
 elf_firmware_t f={0};if(elf_read_firmware(argv[1],&f)<0)fail("ELF load failed");
 avr=avr_make_mcu_by_name("atmega328");if(!avr||avr_init(avr))fail("ATmega328 unavailable");
 if(avr->flashend+1!=32768||avr->ramend-avr->ioend!=2048||avr->e2end+1!=1024)fail("unexpected MCU memory geometry");
 if(f.flashbase!=0||f.flashsize>32768||f.datasize+f.bsssize>1200||f.eesize>1024)fail("firmware exceeds memory budget");
 avr_load_firmware(avr,&f);avr->frequency=16000000; // synthetic fixture only, board frequency unknown
 uint16_t status=symbol(&f,"lab_status",1),in=symbol(&f,"lab_input",65),out=symbol(&f,"lab_output",26);
 wait_status(status,1);lowest_sp=avr->data[R_SPL]|(avr->data[R_SPH]<<8);track_stack=1;
 memcpy(avr->data+in,input,65);avr->data[status]=2;wait_status(status,3);
 uint64_t first_cycle=avr->cycle,max_request_cycles=0;
 fprintf(output,"{\"ticksPerPulse\":120,\"events\":[");int first=1,finished=0;
 for(int i=0;i<513;++i){
  uint64_t begin=avr->cycle;avr->data[status]=4;wait_status(status,5);
  uint64_t elapsed=avr->cycle-begin;if(elapsed>max_request_cycles)max_request_cycles=elapsed;
  if(avr->data[status]==6){finished=1;break;}
  uint32_t cycle=(uint32_t)u16(out)|((uint32_t)u16(out+2)<<16);
  if(cycle>0){finished=1;break;}
  uint8_t gates=avr->data[out+9];if(gates>4)fail("corrupt gate count");
  if(!first)fprintf(output,",");
  first=0;
  fprintf(output,"{\"stage\":%u,\"segment\":%u,\"repeat\":%u,\"pulse\":%u,\"note\":%u,\"gates\":[",avr->data[out+6]+1,avr->data[out+4]+1,avr->data[out+5]+1,avr->data[out+7]+1,avr->data[out+8]);
  for(uint8_t j=0;j<gates;++j){if(j)fprintf(output,",");fprintf(output,"[%u,%u]",u16(out+10+4*j),u16(out+12+4*j));}
  fprintf(output,"]}");
 }
 if(!finished)fail("phrase exceeded event bound");
 fprintf(output,"],\"simulation\":{\"engine\":\"simavr\",\"requestedMcu\":\"atmega328\",\"modelSignature\":\"%02x%02x%02x\",\"fixtureHz\":16000000,\"flashCapacity\":32768,\"sramCapacity\":2048,\"eepromCapacity\":1024,\"flashImageBytes\":%u,\"staticSramBytes\":%u,\"observedStackBytes\":%u,\"cycles\":%llu,\"maxRequestCycles\":%llu,\"boardEmulated\":false}}\n",avr->signature[0],avr->signature[1],avr->signature[2],f.flashsize,f.datasize+f.bsssize,avr->ramend-lowest_sp,(unsigned long long)(avr->cycle-first_cycle),(unsigned long long)max_request_cycles);
 fflush(output);avr_terminate(avr);return 0;
}
