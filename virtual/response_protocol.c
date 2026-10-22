#include "response_protocol.h"
#include <string.h>

void metro_stled_init(metro_stled_t *s,uint8_t k0,uint8_t k1) {
    memset(s,0,sizeof(*s));s->key[0]=k0;s->key[1]=k1;
}
static void command(metro_stled_t *s,uint8_t value) {
    s->command_seen=true;s->command=value;++s->commands;
    s->page=(value>>3)&3;s->address=value&7;
    if(value&0x40){
        // Deliberate subset: sequential key byte1+byte2, including unused bit7.
        if((value&0x7f)!=0x49){s->invalid=true;++s->unsupported;return;}
        s->reading=true;s->read_bits=0;s->ready=false;++s->key_requests;
        memcpy(s->snapshot,s->key,2);
    } else if((value&0x5f)==0x0d) s->display_on=true;
    else if((value&0x5f)==0x0e) s->display_on=false;
}
static void write_byte(metro_stled_t *s,uint8_t value) {
    static const uint8_t sizes[]={6,1,4,4};
    if((s->command&0x5f)==0x0d||(s->command&0x5f)==0x0e||
       s->address>=sizes[s->page]){s->invalid=true;++s->unsupported;return;}
    s->pages[s->page][s->address]=value;++s->write_bytes;
    if(!(s->command&0x20))++s->address;
}
void metro_stled_update(metro_stled_t *s,bool stb,bool clk,bool host_drives,
                        bool data,bool gpio_valid) {
    if(!s->initialized){s->initialized=true;s->stb=stb;s->clk=clk;return;}
    bool rising=!s->clk&&clk,falling=s->clk&&!clk;
    if(s->stb&&!stb){
        s->open=true;s->invalid=!gpio_valid;s->command_seen=false;
        s->reading=false;s->ready=false;s->bits=0;s->shift=0;s->read_bits=0;
        ++s->frames;
    }
    if(!s->stb&&stb&&s->open){
        if(s->bits)++s->partial_bytes;
        if(s->reading&&s->read_bits<16)++s->partial_reads;
        s->open=false;s->reading=false;s->ready=false;
    }
    if(s->open&&!stb&&!s->invalid){
        if(!gpio_valid){s->invalid=true;++s->direction_faults;}
        else if(s->reading){
            // First response bit appears on the falling edge after command bit7.
            if(falling&&s->read_bits>=16){s->invalid=true;++s->unsupported;}
            if(falling&&s->read_bits<16){
                if(host_drives){s->invalid=true;++s->direction_faults;}
                else s->ready=true;
            }
            if(rising&&s->ready){
                if(host_drives){s->invalid=true;++s->direction_faults;}
                else {++s->read_bits;s->ready=false;if(s->read_bits==16)++s->key_complete;}
            }
        } else if(rising){
            if(!host_drives){s->invalid=true;++s->direction_faults;}
            else {
                if(data)s->shift|=(uint8_t)(1u<<s->bits);
                if(++s->bits==8){uint8_t value=s->shift;s->bits=0;s->shift=0;
                    if(!s->command_seen)command(s,value);else write_byte(s,value);
                }
            }
        }
    }
    // Driving during the receive interval is a fault even without a clock edge.
    if(s->open&&!s->invalid&&s->reading&&s->ready&&host_drives){
        s->invalid=true;++s->direction_faults;
    }
    s->stb=stb;s->clk=clk;
}
bool metro_stled_output(const metro_stled_t *s,bool host_drives,bool *bit) {
    if(!s->open||s->invalid||!s->reading||!s->ready||s->read_bits>=16||host_drives)return false;
    *bit=(s->snapshot[s->read_bits/8]>>(s->read_bits%8))&1;return true;
}
void metro_scan_select(metro_scan_t *s,bool selected) {
    if(selected&&!s->selected){s->count=0;s->invalid=false;++s->frames;}
    if(!selected&&s->selected&&s->count!=2)++s->partial;
    s->selected=selected;
}
bool metro_scan_exchange(metro_scan_t *s,uint8_t tx,uint8_t *rx) {
    if(!s->selected||s->invalid)return false;
    if(s->count==0){
        if(tx&0xc7){s->invalid=true;++s->malformed;return false;}
        s->channel=(tx>>3)&7;s->latched=s->words[s->channel];
        *rx=s->latched>>8;s->count=1;++s->responses;return true;
    }
    if(s->count==1&&tx==0){
        *rx=s->latched&255;s->count=2;++s->complete;++s->responses;
        ++s->channel_reads[s->channel];return true;
    }
    s->invalid=true;++s->malformed;return false;
}
