#ifndef METROPOLIS_SYNTHETIC_PERIPHERALS_H
#define METROPOLIS_SYNTHETIC_PERIPHERALS_H

#include <stdint.h>

namespace metro {
namespace virtualhw {

// Datasheet-level logical model only. It does not claim rev010 routing.
class Hc4051 {
public:
    Hc4051();
    void setChannel(uint8_t index, uint16_t value);
    void setSelect(bool s0, bool s1, bool s2);
    void setEnabled(bool enabled); // logical enabled == physical E low
    bool connected() const;
    uint8_t selectedChannel() const;
    uint16_t output() const;
private:
    uint16_t channels_[8];
    uint8_t selected_;
    bool enabled_;
};

// Datasheet-level 74HC165 logical model. Q7 is bit 7 of the shift register.
class Hc165 {
public:
    Hc165();
    void setParallelInputs(uint8_t value);
    void setParallelLoadHigh(bool high); // PL low asynchronously loads D0..D7
    void setClockEnableHigh(bool high);  // CE high blocks CP
    void setSerialInput(bool high);
    void clockRising();
    bool q7() const;
    uint8_t registerValue() const;
private:
    void asyncLoadIfSelected();
    uint8_t parallel_;
    uint8_t shift_;
    bool plHigh_;
    bool ceHigh_;
    bool serialIn_;
};

// Deliberately high-level STLED316S contract model. It models key-buffer and
// IRQ semantics plus display memory, not serial timing or rev010 wiring.
class Stled316s {
public:
    Stled316s();
    void setKey(uint8_t keyRow, uint8_t scanColumn, bool pressed);
    uint8_t keyByte(uint8_t keyRow) const;
    uint8_t readKeyByte(uint8_t keyRow);
    bool irqActiveLow() const;
    void writeDisplayByte(uint8_t digit, uint8_t value);
    uint8_t displayByte(uint8_t digit) const;
    void setDisplayOn(bool on);
    bool displayOn() const;
private:
    uint8_t key_[2];
    uint8_t display_[7];
    uint8_t readMask_;
    bool irq_;
    bool displayOn_;
};

} // namespace virtualhw
} // namespace metro

#endif
