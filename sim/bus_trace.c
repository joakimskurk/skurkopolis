#include "bus_trace.h"
#include <sim_io.h>
#include <avr_spi.h>
#include <stdlib.h>

typedef struct {
    const char *name;
    uint16_t address;
    avr_io_read_t read;
    avr_io_write_t write;
    void *read_param, *write_param;
    uint64_t reads, writes;
} hook_t;
#define H(n,a) {.name=n,.address=a}
static hook_t hooks[] = {
    H("PINB",0x23),H("DDRB",0x24),H("PORTB",0x25),
    H("PINC",0x26),H("DDRC",0x27),H("PORTC",0x28),
    H("PIND",0x29),H("DDRD",0x2a),H("PORTD",0x2b),
    H("SPCR",0x4c),H("SPSR",0x4d),H("SPDR",0x4e),
    H("ADCL",0x78),H("ADCH",0x79),H("ADCSRA",0x7a),
    H("ADCSRB",0x7b),H("ADMUX",0x7c)
};
typedef struct {
    uint64_t cycle;
    uint32_t pc;
    uint16_t address;
    uint8_t kind,value,port[3],ddr[3],spcr,spsr;
} event_t;
static event_t *events;
static uint32_t capacity,stored;
static uint64_t start_cycle,before_window,dropped,spi_outputs,count_only_reads;
static avr_irq_t *spi_irq;

static void append(avr_t *avr,uint8_t kind,uint16_t address,uint8_t value) {
    if(avr->cycle<start_cycle){++before_window;return;}
    if(stored==capacity){++dropped;return;}
    event_t *e=&events[stored++];
    e->cycle=avr->cycle;e->pc=avr->pc;e->kind=kind;e->address=address;e->value=value;
    for(unsigned i=0;i<3;++i){e->ddr[i]=avr->data[0x24+3*i];e->port[i]=avr->data[0x25+3*i];}
    e->spcr=avr->data[0x4c];e->spsr=avr->data[0x4d];
}
static uint8_t read_hook(avr_t *avr,avr_io_addr_t address,void *param) {
    hook_t *h=param;
    uint8_t value=h->read?h->read(avr,address,h->read_param):avr->data[address];
    ++h->reads;
    // Keep polling and read/modify/write overhead in counters, not event storage.
    if(address==0x23||address==0x26||address==0x29||address==0x4e||address>=0x78)
        append(avr,0,address,value);
    else ++count_only_reads;
    return value;
}
static void write_hook(avr_t *avr,avr_io_addr_t address,uint8_t value,void *param) {
    hook_t *h=param;
    if(h->write)h->write(avr,address,value,h->write_param);else avr->data[address]=value;
    ++h->writes;append(avr,1,address,value);
}
static void spi_output(struct avr_irq_t *irq,uint32_t value,void *param) {
    (void)irq;++spi_outputs;append(param,2,0x4e,(uint8_t)value);
}
void bus_trace_init(avr_t *avr,uint32_t limit,uint64_t start) {
    capacity=limit;start_cycle=start;events=calloc(limit,sizeof(*events));
    if(!events){fprintf(stderr,"bus trace allocation failed\n");exit(1);}
    // Wrap the existing callbacks exactly once, including shared dispatchers.
    // Do not register a second device writer or change IRQ filtering flags.
    for(unsigned i=0;i<sizeof(hooks)/sizeof(hooks[0]);++i){
        hook_t *h=&hooks[i];unsigned a=AVR_DATA_TO_IO(h->address);
        h->read=avr->io[a].r.c;h->read_param=avr->io[a].r.param;
        h->write=avr->io[a].w.c;h->write_param=avr->io[a].w.param;
        avr->io[a].r.c=read_hook;avr->io[a].r.param=h;
        avr->io[a].w.c=write_hook;avr->io[a].w.param=h;
    }
    spi_irq=avr_io_getirq(avr,AVR_IOCTL_SPI_GETIRQ(0),SPI_IRQ_OUTPUT);
    if(!spi_irq){fprintf(stderr,"SPI output IRQ unavailable\n");exit(1);}
    avr_irq_register_notify(spi_irq,spi_output,avr);
}
void bus_trace_report(FILE *out) {
    fprintf(out,",\"busTrace\":{\"schema\":1,\"scope\":\"simavr_callback_observations\",\"startCycle\":%llu,\"capacity\":%u,\"stored\":%u,\"beforeWindow\":%llu,\"dropped\":%llu,\"truncated\":%s,\"spiOutputs\":%llu,\"countOnlyReads\":%llu,\"readEventPolicy\":\"PINx_SPDR_ADC_only_other_reads_counted\",\"accessCounts\":[",
        (unsigned long long)start_cycle,capacity,stored,(unsigned long long)before_window,
        (unsigned long long)dropped,dropped?"true":"false",(unsigned long long)spi_outputs,(unsigned long long)count_only_reads);
    for(unsigned i=0;i<sizeof(hooks)/sizeof(hooks[0]);++i){
        hook_t *h=&hooks[i];if(i)fputc(',',out);
        fprintf(out,"{\"name\":\"%s\",\"address\":%u,\"reads\":%llu,\"writes\":%llu}",h->name,h->address,(unsigned long long)h->reads,(unsigned long long)h->writes);
    }
    fputs("],\"events\":[",out);
    for(uint32_t i=0;i<stored;++i){event_t *e=&events[i];if(i)fputc(',',out);
        fprintf(out,"{\"cycle\":%llu,\"pc\":%u,\"kind\":\"%s\",\"address\":%u,\"value\":%u,\"port\":[%u,%u,%u],\"ddr\":[%u,%u,%u],\"spcr\":%u,\"spsr\":%u}",
            (unsigned long long)e->cycle,e->pc,e->kind==0?"read":e->kind==1?"write":"spi_output",e->address,e->value,
            e->port[0],e->port[1],e->port[2],e->ddr[0],e->ddr[1],e->ddr[2],e->spcr,e->spsr);
    }
    fputs("]}",out);
}
void bus_trace_close(avr_t *avr) {
    for(unsigned i=0;i<sizeof(hooks)/sizeof(hooks[0]);++i){hook_t *h=&hooks[i];unsigned a=AVR_DATA_TO_IO(h->address);
        avr->io[a].r.c=h->read;avr->io[a].r.param=h->read_param;
        avr->io[a].w.c=h->write;avr->io[a].w.param=h->write_param;
    }
    avr_irq_unregister_notify(spi_irq,spi_output,avr);free(events);events=NULL;
}
