#include "synthetic_peripherals.h"
#include <assert.h>
#include <stdio.h>

using metro::virtualhw::Hc4051;
using metro::virtualhw::Hc165;
using metro::virtualhw::Stled316s;

static void test4051() {
    Hc4051 mux;
    for (uint8_t i = 0; i < 8; ++i) mux.setChannel(i, static_cast<uint16_t>(100 + i));
    for (uint8_t i = 0; i < 8; ++i) {
        mux.setSelect((i & 1u) != 0, (i & 2u) != 0, (i & 4u) != 0);
        assert(mux.selectedChannel() == i);
        assert(mux.connected());
        assert(mux.output() == 100 + i);
    }
    mux.setEnabled(false);
    assert(!mux.connected());
    assert(mux.output() == 0);
}

static void test165() {
    Hc165 sr;
    sr.setParallelInputs(0xA5u); // D7..D0 = 10100101
    sr.setParallelLoadHigh(false);
    assert(sr.registerValue() == 0xA5u);
    sr.setParallelLoadHigh(true);
    const bool expected[8] = {true,false,true,false,false,true,false,true};
    for (uint8_t i = 0; i < 8; ++i) {
        assert(sr.q7() == expected[i]);
        sr.clockRising();
    }
    sr.setParallelInputs(0xC0u);
    sr.setParallelLoadHigh(false);
    sr.setParallelLoadHigh(true);
    sr.setClockEnableHigh(true);
    const uint8_t held = sr.registerValue();
    sr.clockRising();
    assert(sr.registerValue() == held);
    sr.setClockEnableHigh(false);
    sr.clockRising();
    assert(sr.registerValue() != held);
    sr.setParallelLoadHigh(false);
    sr.setParallelInputs(0x3Cu);
    assert(sr.registerValue() == 0x3Cu); // asynchronous while PL is low
}

static void testStled() {
    Stled316s led;
    assert(!led.displayOn());
    assert(!led.irqActiveLow());
    led.setDisplayOn(true);
    led.writeDisplayByte(3, 0x5Au);
    assert(led.displayOn());
    assert(led.displayByte(3) == 0x5Au);

    led.setKey(0, 0, true);
    led.setKey(1, 7, true);
    assert(led.keyByte(0) == 0x01u); // SEG1/KS1 is LSB of KEY1 byte
    assert(led.keyByte(1) == 0x80u); // SEG8/KS8 is MSB of KEY2 byte
    assert(led.irqActiveLow());
    assert(led.readKeyByte(0) == 0x01u);
    assert(led.irqActiveLow()); // full key buffer has not yet been read
    assert(led.readKeyByte(1) == 0x80u);
    assert(!led.irqActiveLow());

    led.setKey(0, 0, false);
    assert(led.irqActiveLow());
}

int main() {
    test4051();
    test165();
    testStled();
    puts("PASS synthetic peripheral contracts: 74HC4051, 74HC165, STLED316S key/display semantics");
    return 0;
}
