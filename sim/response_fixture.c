// Explicit hypothesis fixture, independent of the verified hardware map.
#include "response_fixture.h"
#include "spi_timing.h"
#include "../virtual/response_protocol.h"
#include <sim_io.h>
#include <avr_spi.h>
#include <stdlib.h>
#include <string.h>

typedef struct {uint16_t address;avr_io_write_t write;void *param;} hook_t;
static hook_t hooks[]={
    {0x23,NULL,NULL},{0x24,NULL,NULL},{0x25,NULL,NULL},
    {0x26,NULL,NULL},{0x27,NULL,NULL},{0x28,NULL,NULL},
    {0x29,NULL,NULL},{0x2a,NULL,NULL},{0x2b,NULL,NULL},
    {0x4c,NULL,NULL},{0x4e,NULL,NULL}
};
static avr_io_read_t pin_read;
static void *pin_read_param;
static avr_irq_t *spi_in,*spi_out;
static metro_stled_t stled;
static metro_scan_t scans[2]; // PC5, PC4; synthetic 16-bit words, MSB then LSB.
static uint8_t selected,pending_select,pending_tx;
static uint64_t epoch,pending_epoch,pin_overrides,spi_responses,spi_unserved,spi_faults;
static bool pending,pending_valid;
typedef struct {uint64_t cycle,applied;uint8_t key[2];} key_event_t;
static key_event_t events[32];
static unsigned event_count,event_index;

static void fail(const char *why){fprintf(stderr,"response fixture: %s\n",why);exit(1);}
static unsigned byte(FILE *in){int b=fgetc(in);if(b==EOF)fail("truncated config");return (unsigned)b;}
static uint64_t little(FILE *in,unsigned count){uint64_t v=0;for(unsigned i=0;i<count;++i)v|=(uint64_t)byte(in)<<(8*i);return v;}
static uint8_t selects(avr_t *avr){
    uint8_t b=avr->data[0x25],c=avr->data[0x28],db=avr->data[0x24],dc=avr->data[0x27];
    return ((db&4)&&!(b&4)?1:0)|((dc&32)&&!(c&32)?2:0)|((dc&16)&&!(c&16)?4:0);
}
static void update(avr_t *avr){
    uint8_t now=selects(avr);
    if(now!=selected){++epoch;selected=now;}
    metro_scan_select(&scans[0],now&2);metro_scan_select(&scans[1],now&4);
    bool valid=(avr->data[0x2a]&64)&&(avr->data[0x24]&32)&&!(avr->data[0x4c]&64);
    metro_stled_update(&stled,avr->data[0x2b]&64,avr->data[0x25]&32,
                        avr->data[0x24]&8,avr->data[0x25]&8,valid);
}
static uint8_t read_pin(avr_t *avr,avr_io_addr_t address,void *param){
    (void)param;uint8_t value=pin_read?pin_read(avr,address,pin_read_param):avr->data[address];bool bit;
    // A sampled input adapter: no pin IRQ, pull resistor or physical bus model.
    if(metro_stled_output(&stled,avr->data[0x24]&8,&bit)){
        value=(value&~8)|(bit?8:0);++pin_overrides;
    }
    return value;
}
static void write_hook(avr_t *avr,avr_io_addr_t address,uint8_t value,void *param){
    hook_t *h=param;
    if(address==0x4e){
        bool busy=pending;
        pending=true;pending_tx=value;pending_select=selected;pending_epoch=epoch;
        pending_valid=!busy&&((avr->data[0x4c]&0x50)==0x50)&&
                      (selected==1||selected==2||selected==4);
        if(!pending_valid)++spi_faults;
    }
    if(h->write)h->write(avr,address,value,h->param);else avr->data[address]=value;
    update(avr);
}
static void spi_complete(struct avr_irq_t *irq,uint32_t value,void *param){
    (void)irq;avr_t *avr=param;uint8_t rx;
    bool valid=pending&&pending_valid&&pending_epoch==epoch&&selected==pending_select&&
               pending_tx==(uint8_t)value&&((avr->data[0x4c]&0x50)==0x50);
    if(!valid){++spi_unserved;if(pending_valid)++spi_faults;}
    else if(selected==1)++spi_unserved; // unidentified PB2 peripheral, intentionally no reply
    else {
        metro_scan_t *s=&scans[selected==2?0:1];
        if(metro_scan_exchange(s,(uint8_t)value,&rx)){
            avr_raise_irq(spi_in,rx);++spi_responses;
        } else ++spi_unserved;
    }
    pending=false;
}
void response_fixture_init(avr_t *avr,const char *path){
    FILE *in=fopen(path,"rb");if(!in)fail("cannot open config");
    char magic[8];if(fread(magic,1,8,in)!=8||memcmp(magic,"SKFX0001",8))fail("invalid config magic");
    uint8_t k0=byte(in),k1=byte(in);metro_stled_init(&stled,k0,k1);
    for(unsigned d=0;d<2;++d)for(unsigned c=0;c<8;++c)scans[d].words[c]=(uint16_t)little(in,2);
    event_count=byte(in);if(event_count>32)fail("too many events");
    for(unsigned i=0;i<event_count;++i){
        events[i].cycle=little(in,8);events[i].key[0]=byte(in);events[i].key[1]=byte(in);
        if(events[i].cycle>100000000||(i&&events[i].cycle<=events[i-1].cycle))fail("invalid event cycle");
    }
    if(fgetc(in)!=EOF)fail("trailing config data");
    fclose(in);
    for(unsigned i=0;i<sizeof(hooks)/sizeof(hooks[0]);++i){hook_t *h=&hooks[i];unsigned a=AVR_DATA_TO_IO(h->address);
        h->write=avr->io[a].w.c;h->param=avr->io[a].w.param;
        avr->io[a].w.c=write_hook;avr->io[a].w.param=h;
    }
    unsigned a=AVR_DATA_TO_IO(0x23);pin_read=avr->io[a].r.c;pin_read_param=avr->io[a].r.param;
    avr->io[a].r.c=read_pin;avr->io[a].r.param=NULL;
    spi_in=avr_io_getirq(avr,AVR_IOCTL_SPI_GETIRQ(0),SPI_IRQ_INPUT);
    spi_out=avr_io_getirq(avr,AVR_IOCTL_SPI_GETIRQ(0),SPI_IRQ_OUTPUT);
    if(!spi_in||!spi_out)fail("SPI IRQ missing");
    avr_irq_register_notify(spi_out,spi_complete,avr);update(avr);
}
void response_fixture_tick(avr_t *avr){
    while(event_index<event_count&&events[event_index].cycle<=avr->cycle){
        key_event_t *e=&events[event_index++];e->applied=avr->cycle;
        stled.key[0]=e->key[0];stled.key[1]=e->key[1];
    }
}
void response_fixture_report(FILE *out){
    fprintf(out,",\"responseFixture\":{\"profile\":\"rev010-hypothesis-v1\",\"boardEmulated\":false,\"spiTiming\":\"%s\",\"keyInputAdapter\":\"sampled_PINB3_no_IRQ\",\"stled\":{\"frames\":%llu,\"commands\":%llu,\"keyRequests\":%llu,\"keyComplete\":%llu,\"partialReads\":%llu,\"pinReadOverrides\":%llu,\"writeBytes\":%llu,\"unsupported\":%llu,\"directionFaults\":%llu,\"partialBytes\":%llu,\"displayOn\":%s,\"keyBytes\":[%u,%u],\"pages\":[",
        spi_timing_name(),(unsigned long long)stled.frames,(unsigned long long)stled.commands,(unsigned long long)stled.key_requests,
        (unsigned long long)stled.key_complete,(unsigned long long)stled.partial_reads,(unsigned long long)pin_overrides,
        (unsigned long long)stled.write_bytes,(unsigned long long)stled.unsupported,(unsigned long long)stled.direction_faults,
        (unsigned long long)stled.partial_bytes,stled.display_on?"true":"false",stled.key[0],stled.key[1]);
    for(unsigned p=0;p<4;++p){if(p)fputc(',',out);fputc('[',out);
        unsigned size=p==0?6:p==1?1:4;for(unsigned i=0;i<size;++i){if(i)fputc(',',out);fprintf(out,"%u",stled.pages[p][i]);}fputc(']',out);}
    fprintf(out,"]},\"spiResponses\":%llu,\"spiUnserved\":%llu,\"spiFaults\":%llu,\"scans\":[",
        (unsigned long long)spi_responses,(unsigned long long)spi_unserved,(unsigned long long)spi_faults);
    for(unsigned d=0;d<2;++d){metro_scan_t *s=&scans[d];if(d)fputc(',',out);
        fprintf(out,"{\"select\":\"%s\",\"frames\":%llu,\"complete\":%llu,\"partial\":%llu,\"malformed\":%llu,\"responses\":%llu,\"channelReads\":[",
            d?"PC4":"PC5",(unsigned long long)s->frames,(unsigned long long)s->complete,(unsigned long long)s->partial,
            (unsigned long long)s->malformed,(unsigned long long)s->responses);
        for(unsigned c=0;c<8;++c){if(c)fputc(',',out);fprintf(out,"%llu",(unsigned long long)s->channel_reads[c]);}fputs("]}",out);
    }
    fprintf(out,"],\"eventsApplied\":%u,\"keyEvents\":[",event_index);
    for(unsigned i=0;i<event_count;++i){if(i)fputc(',',out);
        fprintf(out,"{\"requestedCycle\":%llu,\"applied\":%s,\"appliedCycle\":%llu,\"bytes\":[%u,%u]}",
            (unsigned long long)events[i].cycle,i<event_index?"true":"false",(unsigned long long)events[i].applied,events[i].key[0],events[i].key[1]);}
    fputs("]}",out);
}
void response_fixture_close(avr_t *avr){
    avr_irq_unregister_notify(spi_out,spi_complete,avr);
    for(unsigned i=0;i<sizeof(hooks)/sizeof(hooks[0]);++i){hook_t *h=&hooks[i];unsigned a=AVR_DATA_TO_IO(h->address);
        avr->io[a].w.c=h->write;avr->io[a].w.param=h->param;}
    unsigned a=AVR_DATA_TO_IO(0x23);avr->io[a].r.c=pin_read;avr->io[a].r.param=pin_read_param;
}
