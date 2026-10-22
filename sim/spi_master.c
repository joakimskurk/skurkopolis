// Explicit master-only register model. No electrical SPI/SS/slave implementation.
#include "spi_master.h"
#include <avr_spi.h>
#include <sim_io.h>
#include <stdlib.h>

enum {SPCR=0x4c,SPSR=0x4d,SPDR=0x4e,SPIF=0x80,WCOL=0x40};
typedef struct {
    avr_io_read_t read;avr_io_write_t write;void *rp,*wp;
} saved_t;
static saved_t saved[3];
static avr_spi_t *native;
static avr_irq_t *output;
static bool enabled,divider,busy,receiving,received,unread;
static uint8_t tx,rx,reply,armed;
static uint64_t writes,starts,completes,collisions,ignored,aborts,unanswered,overruns;
static uint64_t status_reads,data_reads,flag_clears,isr_entries,max_late,config_counts[8];

static void fail(const char *why){fprintf(stderr,"SPI master: %s\n",why);exit(1);}
bool spi_master_enabled(void){return enabled;}
bool spi_master_busy(void){return busy;}
bool spi_master_can_start(avr_t *avr){return !busy&&(avr->data[SPCR]&0x50)==0x50;}
void spi_master_receive(uint8_t value){
    if(!receiving||received)fail("response outside completion window or duplicate response");
    reply=value;received=true;
}
static void acknowledge(avr_t *avr){
    uint8_t clear=armed&avr->data[SPSR];armed=0;
    if(clear&SPIF){avr_clear_interrupt(avr,&native->spi);++flag_clears;}
    if(clear&WCOL)avr->data[SPSR]&=~WCOL;
}
static uint8_t read_status(avr_t *avr,avr_io_addr_t addr,void *param){
    (void)addr;(void)param;++status_reads;
    uint8_t value=avr->data[SPSR]&0xc1;armed|=value&0xc0;return value;
}
static uint8_t read_data(avr_t *avr,avr_io_addr_t addr,void *param){
    (void)addr;(void)param;++data_reads;acknowledge(avr);unread=false;return rx;
}
static avr_cycle_count_t complete(avr_t *avr,avr_cycle_count_t when,void *param){
    (void)param;busy=false;++completes;
    if(avr->cycle>when&&avr->cycle-when>max_late)max_late=avr->cycle-when;
    // Responses use the explicit fixture API, bypassing native SPI_IRQ_INPUT's
    // premature interrupt/flag side effects. An unserved input is synthetic zero.
    receiving=true;received=false;reply=0;
    avr_raise_irq(output,tx);
    receiving=false;if(!received)++unanswered;
    if(unread)++overruns;
    rx=reply;unread=true;avr->data[SPDR]=rx;
    avr_raise_interrupt(avr,&native->spi);
    return 0;
}
static void write_data(avr_t *avr,avr_io_addr_t addr,uint8_t value,void *param){
    (void)addr;(void)param;++writes;acknowledge(avr);
    if(busy){avr->data[SPSR]|=WCOL;++collisions;return;}
    if((avr->data[SPCR]&0x50)!=0x50){++ignored;return;}
    static const unsigned divs[8]={4,16,64,128,2,8,32,64};
    unsigned index=(avr->data[SPCR]&3)|((avr->data[SPSR]&1)<<2);
    ++config_counts[index];++starts;busy=true;tx=value;
    // TX shift state is separate from the retained receive buffer.
    avr_cycle_timer_register(avr,divider?8*divs[index]:avr->frequency/10000,complete,NULL);
}
static void write_status(avr_t *avr,avr_io_addr_t addr,uint8_t value,void *param){
    (void)addr;(void)param;
    avr_core_watch_write(avr,SPSR,(avr->data[SPSR]&0xc0)|(value&1));
}
static void write_control(avr_t *avr,avr_io_addr_t addr,uint8_t value,void *param){
    (void)addr;(void)param;avr_core_watch_write(avr,SPCR,value);
    if(busy&&(value&0x50)!=0x50){
        avr_cycle_timer_cancel(avr,complete,NULL);busy=false;++aborts;
    }
    // If SPIE becomes enabled while SPIF is latched, request the pending ISR.
    if((value&0x80)&&(avr->data[SPSR]&SPIF))avr_raise_interrupt(avr,&native->spi);
}
static void isr(struct avr_irq_t *irq,uint32_t value,void *param){
    (void)irq;(void)param;if(value){++isr_entries;armed&=~SPIF;}
    // simavr's interrupt dispatcher clears SPIF on vector entry.
}
void spi_master_init(avr_t *avr,bool divider_timing){
    if(enabled)fail("already installed");
    unsigned a=AVR_DATA_TO_IO(SPDR);native=avr->io[a].w.param;
    if(!native||!avr->io[a].w.c||native->r_spcr!=SPCR||native->r_spsr!=SPSR||native->r_spdr!=SPDR)
        fail("unexpected native simavr SPI layout");
    for(unsigned i=0;i<3;++i){unsigned n=AVR_DATA_TO_IO(SPCR+i);
        saved[i]=(saved_t){avr->io[n].r.c,avr->io[n].w.c,avr->io[n].r.param,avr->io[n].w.param};
    }
    output=avr_io_getirq(avr,AVR_IOCTL_SPI_GETIRQ(0),SPI_IRQ_OUTPUT);
    if(!output||native->spi.vector!=17||native->spi.raise_sticky)fail("unexpected SPI IRQ configuration");
    avr->io[AVR_DATA_TO_IO(SPCR)].w.c=write_control;
    avr->io[AVR_DATA_TO_IO(SPSR)].r.c=read_status;
    avr->io[AVR_DATA_TO_IO(SPSR)].w.c=write_status;
    avr->io[a].r.c=read_data;avr->io[a].w.c=write_data;
    avr_irq_register_notify(native->spi.irq+AVR_INT_IRQ_RUNNING,isr,NULL);
    enabled=true;divider=divider_timing;
}
void spi_master_report(FILE *out){
    fprintf(out,",\"spiMaster\":{\"profile\":\"avr-master-v1\",\"timing\":\"%s\",\"writes\":%llu,\"starts\":%llu,\"completions\":%llu,\"collisions\":%llu,\"ignoredNonMasterWrites\":%llu,\"abortedTransfers\":%llu,\"unansweredTransfers\":%llu,\"unreadOverwrites\":%llu,\"statusReads\":%llu,\"dataReads\":%llu,\"spifAccessClears\":%llu,\"isrEntries\":%llu,\"maxCallbackLatenessCycles\":%llu,\"pendingAtStop\":%s,\"receiveByte\":%u,\"configurationCounts\":[",
        divider?"avr-divider-v1":"simavr1.6_fixed100us",
        (unsigned long long)writes,(unsigned long long)starts,(unsigned long long)completes,
        (unsigned long long)collisions,(unsigned long long)ignored,(unsigned long long)aborts,
        (unsigned long long)unanswered,(unsigned long long)overruns,(unsigned long long)status_reads,
        (unsigned long long)data_reads,(unsigned long long)flag_clears,(unsigned long long)isr_entries,
        (unsigned long long)max_late,busy?"true":"false",rx);
    for(unsigned i=0;i<8;++i){if(i)fputc(',',out);fprintf(out,"%llu",(unsigned long long)config_counts[i]);}
    fputs("]}",out);
}
void spi_master_close(avr_t *avr){
    avr_cycle_timer_cancel(avr,complete,NULL);
    avr_irq_unregister_notify(native->spi.irq+AVR_INT_IRQ_RUNNING,isr,NULL);
    for(unsigned i=0;i<3;++i){unsigned n=AVR_DATA_TO_IO(SPCR+i);
        avr->io[n].r.c=saved[i].read;avr->io[n].r.param=saved[i].rp;
        avr->io[n].w.c=saved[i].write;avr->io[n].w.param=saved[i].wp;
    }
    enabled=false;
}
