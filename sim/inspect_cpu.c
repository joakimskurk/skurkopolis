// Bounded CPU experiment. Optional hypothesis fixture; no verified board or hardware access.
#define _POSIX_C_SOURCE 200809L
#include <sim_avr.h>
#include <sim_io.h>
#include <avr_eeprom.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include "bus_trace.h"
#include "response_fixture.h"
#include "spi_timing.h"
#include "spi_master.h"

typedef struct { const char *name; unsigned address; uint8_t last; uint64_t changes,first; } reg_t;
#define REG(n,a) {n,a,0,0,0}
static reg_t regs[]={
 REG("PINB",0x23),REG("DDRB",0x24),REG("PORTB",0x25),
 REG("PINC",0x26),REG("DDRC",0x27),REG("PORTC",0x28),
 REG("PIND",0x29),REG("DDRD",0x2a),REG("PORTD",0x2b),
 REG("TIFR0",0x35),REG("TIFR1",0x36),REG("TIFR2",0x37),
 REG("EIFR",0x3c),REG("EIMSK",0x3d),REG("EECR",0x3f),
 REG("TCCR0A",0x44),REG("TCCR0B",0x45),REG("OCR0A",0x47),REG("OCR0B",0x48),
 REG("SPCR",0x4c),REG("SPSR",0x4d),REG("SPDR",0x4e),REG("SMCR",0x53),
 REG("MCUSR",0x54),REG("MCUCR",0x55),REG("WDTCSR",0x60),REG("CLKPR",0x61),
 REG("PCICR",0x68),REG("EICRA",0x69),REG("PCMSK0",0x6b),REG("PCMSK1",0x6c),REG("PCMSK2",0x6d),
 REG("TIMSK0",0x6e),REG("TIMSK1",0x6f),REG("TIMSK2",0x70),
 REG("ADCSRA",0x7a),REG("ADCSRB",0x7b),REG("ADMUX",0x7c),
 REG("TCCR1A",0x80),REG("TCCR1B",0x81),REG("OCR1AL",0x88),REG("OCR1AH",0x89),
 REG("TCCR2A",0xb0),REG("TCCR2B",0xb1),REG("TWCR",0xbc),REG("UCSR0B",0xc1)
};
static void fail(const char *why){fprintf(stderr,"cpu inspector: %s\n",why);exit(1);}
static uint64_t number(const char *text,uint64_t lo,uint64_t hi){
 char *end;errno=0;unsigned long long n=strtoull(text,&end,10);
 if(errno||!*text||*end||text[0]=='-'||n<lo||n>hi)fail("invalid numeric bound");
 return n;
}
static void no_sleep(avr_t *avr,avr_cycle_count_t cycles){(void)avr;(void)cycles;}
int main(int argc,char **argv){
 int timing=0,status=0;
 while(argc>1&&strncmp(argv[argc-1],"--spi-",6)==0){
  const char *option=argv[--argc];
  if(!strcmp(option,"--spi-timing=avr-divider-v1")&&!timing)timing=1;
  else if(!strcmp(option,"--spi-status=avr-master-v1")&&!status)status=1;
  else fail("unknown or duplicate SPI option");
 }
 if(argc<4||argc>7)fail("usage: cpu_inspector padded.bin cycles fixture-hz [trace-capacity trace-start-cycle] [fixture.bin]");
 uint64_t limit=number(argv[2],1,100000000),hz=number(argv[3],100000,20000000);
 uint32_t trace_capacity=argc>=6?(uint32_t)number(argv[4],1,100000):0;
 uint64_t trace_start=argc>=6?number(argv[5],0,limit-1):0;
 const char *fixture=argc==5?argv[4]:argc==7?argv[6]:NULL;
 uint8_t flash[32768],eeprom[1024];
 FILE *in=fopen(argv[1],"rb");if(!in)fail("cannot read input");
 if(fread(flash,1,sizeof(flash),in)!=sizeof(flash)||fgetc(in)!=EOF)fail("expected exactly 32768 flash bytes");
 fclose(in);
 FILE *out=fdopen(dup(STDOUT_FILENO),"w");if(!out||dup2(STDERR_FILENO,STDOUT_FILENO)<0)fail("output setup");
 avr_t *avr=avr_make_mcu_by_name("atmega328");if(!avr||avr_init(avr))fail("MCU model unavailable");
 if(avr->flashend+1!=32768||avr->ramend-avr->ioend!=2048||avr->e2end+1!=1024)fail("model geometry mismatch");
 avr->frequency=(uint32_t)hz;avr->sleep=no_sleep;avr->run_cycle_limit=1;
 avr->vcc=avr->avcc=avr->aref=5000; // declared synthetic fixture, never a board measurement
 avr_loadcode(avr,flash,sizeof(flash),0);
 memset(eeprom,0xff,sizeof(eeprom));avr_eeprom_desc_t ee={.ee=eeprom,.offset=0,.size=sizeof(eeprom)};
 // simavr EEPROM ioctl returns -1 even on handled operations in some 1.6 builds.
 // Verify data via GET rather than relying on that return code.
 avr_ioctl(avr,AVR_IOCTL_EEPROM_SET,&ee);
 avr_eeprom_desc_t check={.ee=NULL,.offset=0,.size=sizeof(eeprom)};avr_ioctl(avr,AVR_IOCTL_EEPROM_GET,&check);
 if(!check.ee||check.size!=1024||memcmp(check.ee,eeprom,1024))fail("EEPROM fixture initialization failed");
 if(status)spi_master_init(avr,timing);
 else if(timing)spi_timing_init(avr);
 if(fixture)response_fixture_init(avr,fixture);
 if(trace_capacity)bus_trace_init(avr,trace_capacity,trace_start);
 const unsigned nr=sizeof(regs)/sizeof(regs[0]);
 for(unsigned i=0;i<nr;++i)regs[i].last=avr->data[regs[i].address];
 uint64_t visits[16384]={0},calls=0,stalled=0,previous=0;
 const char *reason="cycle_limit";
 while(avr->cycle<limit){
  if(fixture)response_fixture_tick(avr);
  if(avr->pc>=32768||(avr->pc&1)) {reason="invalid_pc";break;}
  ++visits[avr->pc/2];++calls;previous=avr->cycle;
  int state=avr_run(avr);
  for(unsigned i=0;i<nr;++i){uint8_t value=avr->data[regs[i].address];
   if(value!=regs[i].last){if(!regs[i].changes)regs[i].first=avr->cycle;++regs[i].changes;regs[i].last=value;}}
  if(state==cpu_Crashed){reason="cpu_crashed";break;}
  if(state==cpu_Done){reason="cpu_done";break;}
  if(avr->cycle==previous){if(++stalled>1000){reason="no_cycle_progress";break;}}else stalled=0;
  if(calls>limit+10000){reason="call_limit";break;}
 }
 fprintf(out,"{\"scope\":\"%s\",\"requestedMcu\":\"atmega328\",\"modelSignature\":\"%02x%02x%02x\",\"fixtureHz\":%llu,\"fixtureMillivolts\":5000,\"initialEeprom\":\"all_ff\",\"fuses\":\"simavr_defaults_unmeasured\",\"cycleLimit\":%llu,\"cycles\":%llu,\"runCalls\":%llu,\"finalPc\":%u,\"cpuState\":%d,\"stopReason\":\"%s\",\"boardEmulated\":false,\"registers\":[",fixture?"synthetic_response_hypothesis":"cpu_only_unwired",avr->signature[0],avr->signature[1],avr->signature[2],(unsigned long long)hz,(unsigned long long)limit,(unsigned long long)avr->cycle,(unsigned long long)calls,avr->pc,avr->state,reason);
 for(unsigned i=0;i<nr;++i){if(i)fprintf(out,",");fprintf(out,"{\"name\":\"%s\",\"dataAddress\":%u,\"finalValue\":%u,\"observedChanges\":%llu,\"firstChangeCycle\":%llu}",regs[i].name,regs[i].address,regs[i].last,(unsigned long long)regs[i].changes,(unsigned long long)regs[i].first);}
 fprintf(out,"],\"topPcSamples\":[");
 for(unsigned j=0;j<10;++j){unsigned at=0;for(unsigned i=1;i<16384;++i)if(visits[i]>visits[at])at=i;
  if(!visits[at])break;
  if(j)fprintf(out,",");
  fprintf(out,"{\"byteAddress\":%u,\"samples\":%llu}",at*2,(unsigned long long)visits[at]);visits[at]=0;
 }
 fputs("]",out);
 if(trace_capacity){bus_trace_report(out);bus_trace_close(avr);}
 if(fixture){response_fixture_report(out,timing?"avr-divider-v1":"simavr1.6_fixed100us");response_fixture_close(avr);}
 if(status){spi_master_report(out);spi_master_close(avr);}
 else if(timing){spi_timing_report(out);spi_timing_close(avr);}
 fprintf(out,"}\n");fflush(out);avr_terminate(avr);
 return strcmp(reason,"cycle_limit")?2:0;
}
