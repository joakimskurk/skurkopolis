#include "response_protocol.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void begin(metro_stled_t *s){
    metro_stled_update(s,true,false,true,false,true);
    metro_stled_update(s,false,false,true,false,true);
}
static void send(metro_stled_t *s,uint8_t v){
    for(unsigned i=0;i<8;++i){
        metro_stled_update(s,false,false,true,(v>>i)&1,true);
        metro_stled_update(s,false,true,true,(v>>i)&1,true);
    }
}
static void end(metro_stled_t *s){metro_stled_update(s,true,true,true,false,true);}
static unsigned receive(metro_stled_t *s,unsigned n){
    unsigned value=0;
    for(unsigned i=0;i<n;++i){bool bit=false;
        metro_stled_update(s,false,false,false,false,true);
        assert(metro_stled_output(s,false,&bit));if(bit)value|=1u<<i;
        metro_stled_update(s,false,true,false,false,true);
    }
    return value;
}
int main(void){
    // Exhaust every key bit and byte value; no silent MSB/LSB or byte swap.
    for(unsigned value=0;value<256;++value){metro_stled_t s;
        metro_stled_init(&s,(uint8_t)value,(uint8_t)~value);begin(&s);send(&s,0x49);
        s.key[0]=0;s.key[1]=0; // current transaction keeps its command-time snapshot
        assert(receive(&s,16)==(value|((unsigned)(uint8_t)~value<<8)));
        end(&s);assert(s.key_complete==1&&s.direction_faults==0);
        bool b;assert(!metro_stled_output(&s,false,&b));
    }
    metro_stled_t s;bool bit;
    metro_stled_init(&s,0xa5,0x5a);begin(&s);send(&s,0x49);
    assert(!metro_stled_output(&s,false,&bit)); // wait for first falling edge
    (void)receive(&s,5);end(&s);assert(s.partial_reads==1);
    begin(&s);send(&s,0x49);assert(receive(&s,16)==0x5aa5);end(&s);
    assert(s.key_complete==1); // aborted read did not complete
    begin(&s);send(&s,0x49);
    metro_stled_update(&s,false,false,true,false,true);
    assert(s.direction_faults==1&&!metro_stled_output(&s,false,&bit));end(&s);
    begin(&s);send(&s,0x48);assert(s.unsupported==1);end(&s);
    begin(&s);send(&s,0x00);send(&s,1);send(&s,2);end(&s);
    assert(s.pages[0][0]==1&&s.pages[0][1]==2);
    begin(&s);send(&s,0x21);send(&s,9);send(&s,8);end(&s);
    assert(s.pages[0][1]==8); // fixed addressing
    begin(&s);send(&s,0x0d);end(&s);assert(s.display_on);
    begin(&s);send(&s,0x2e);end(&s);assert(!s.display_on);
    begin(&s);send(&s,0x05);send(&s,7);send(&s,8);end(&s);
    assert(s.pages[0][5]==7&&s.unsupported==2); // no invented wrapping
    begin(&s);send(&s,0x00);send(&s,0x55);
    metro_stled_update(&s,false,false,true,true,true);
    metro_stled_update(&s,false,true,true,true,true);end(&s);
    assert(s.pages[0][0]==0x55&&s.partial_bytes==1);
    begin(&s);metro_stled_update(&s,false,true,true,true,false);
    assert(s.invalid);end(&s);

    metro_scan_t scan;memset(&scan,0,sizeof(scan));uint8_t rx;
    for(unsigned c=0;c<8;++c)scan.words[c]=(uint16_t)(0x1234+c*0x101);
    for(unsigned c=0;c<8;++c){
        metro_scan_select(&scan,true);assert(metro_scan_exchange(&scan,c*8,&rx));
        assert(rx==scan.words[c]>>8);assert(metro_scan_exchange(&scan,0,&rx));
        assert(rx==(scan.words[c]&255));metro_scan_select(&scan,false);
        assert(scan.channel_reads[c]==1);
    }
    assert(scan.complete==8&&scan.responses==16);
    assert(!metro_scan_exchange(&scan,0,&rx));
    metro_scan_select(&scan,true);assert(!metro_scan_exchange(&scan,1,&rx));
    metro_scan_select(&scan,false);metro_scan_select(&scan,true);
    assert(metro_scan_exchange(&scan,0,&rx));assert(!metro_scan_exchange(&scan,1,&rx));
    metro_scan_select(&scan,false);assert(scan.malformed==2);
    metro_scan_select(&scan,true);assert(metro_scan_exchange(&scan,0,&rx));
    assert(metro_scan_exchange(&scan,0,&rx));assert(!metro_scan_exchange(&scan,0,&rx));
    puts("PASS response protocols: 256 key-byte pairs, turnaround/abort/direction, write subset, 8 SPI channels and malformed frames");
    return 0;
}
