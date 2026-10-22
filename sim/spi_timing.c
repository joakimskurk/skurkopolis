// Optional simavr 1.6 timer adapter. Native SPI data/flag/IRQ semantics are retained.
#include "spi_timing.h"
#include <avr_spi.h>
#include <stdlib.h>

static avr_io_write_t native_write;
static void *native_param;
static avr_cycle_timer_t native_timer;
static int enabled,pending;
static uint64_t writes,callbacks,busy_writes,nonmaster_writes,max_late;
static uint64_t dividers[8];

static void fail(const char *why){fprintf(stderr,"SPI timing: %s\n",why);exit(1);}
const char *spi_timing_name(void){return enabled?"avr-divider-v1":"simavr1.6_fixed100us";}
static avr_cycle_count_t complete(avr_t *avr,avr_cycle_count_t when,void *param){
    (void)param;pending=0;++callbacks;
    if(avr->cycle>when&&avr->cycle-when>max_late)max_late=avr->cycle-when;
    // Keep simavr's own completion, SPIF and response notification path.
    return native_timer(avr,when,native_param);
}
static void write_spdr(avr_t *avr,avr_io_addr_t address,uint8_t value,void *param){
    (void)param;
    static const unsigned divider[8]={4,16,64,128,2,8,32,64};
    unsigned index=(avr->data[0x4c]&3)|((avr->data[0x4d]&1)<<2);
    ++writes;++dividers[index];
    if((avr->data[0x4c]&0x50)!=0x50)++nonmaster_writes;
    // Retain native overwrite/restart behavior; count it, do not claim WCOL support.
    if(pending){++busy_writes;avr_cycle_timer_cancel(avr,complete,NULL);}
    native_write(avr,address,value,native_param);
    avr_cycle_timer_slot_t *match=NULL;
    for(avr_cycle_timer_slot_t *s=avr->cycle_timers.timer;s;s=s->next){
        if(s->param==native_param){if(match)fail("ambiguous native timer");match=s;}
    }
    if(!match)fail("native SPI timer missing; requires simavr 1.6");
    if(match->when-avr->cycle!=avr->frequency/10000)fail("native SPI timer is not fixed 100 us");
    if(native_timer&&native_timer!=match->timer)fail("native timer changed");
    native_timer=match->timer;
    avr_cycle_timer_cancel(avr,native_timer,native_param);
    pending=1;avr_cycle_timer_register(avr,8*divider[index],complete,NULL);
}
void spi_timing_init(avr_t *avr){
    unsigned a=AVR_DATA_TO_IO(0x4e);
    native_write=avr->io[a].w.c;native_param=avr->io[a].w.param;
    if(!native_write||!native_param)fail("native SPI handler missing");
    avr_spi_t *p=native_param;
    if(p->r_spdr!=0x4e||p->r_spcr!=0x4c||p->r_spsr!=0x4d)fail("unexpected SPI register layout");
    enabled=1;avr->io[a].w.c=write_spdr;avr->io[a].w.param=NULL;
}
void spi_timing_report(FILE *out){
    fprintf(out,",\"spiTiming\":{\"profile\":\"avr-divider-v1\",\"writes\":%llu,\"timerCallbacks\":%llu,\"busyWrites\":%llu,\"nonMasterWrites\":%llu,\"maxCallbackLatenessCycles\":%llu,\"pendingAtStop\":%s,\"configurationCounts\":[",
        (unsigned long long)writes,(unsigned long long)callbacks,(unsigned long long)busy_writes,
        (unsigned long long)nonmaster_writes,(unsigned long long)max_late,pending?"true":"false");
    for(unsigned i=0;i<8;++i){if(i)fputc(',',out);fprintf(out,"%llu",(unsigned long long)dividers[i]);}
    fputs("]}",out);
}
void spi_timing_close(avr_t *avr){
    avr_cycle_timer_cancel(avr,complete,NULL);
    unsigned a=AVR_DATA_TO_IO(0x4e);avr->io[a].w.c=native_write;avr->io[a].w.param=native_param;
    enabled=0;
}
