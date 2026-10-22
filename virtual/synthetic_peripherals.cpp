#include "synthetic_peripherals.h"

namespace metro {
namespace virtualhw {

Hc4051::Hc4051() : selected_(0), enabled_(true) {
    for (uint8_t i = 0; i < 8; ++i) channels_[i] = 0;
}
void Hc4051::setChannel(uint8_t index, uint16_t value) {
    if (index < 8) channels_[index] = value;
}
void Hc4051::setSelect(bool s0, bool s1, bool s2) {
    selected_ = static_cast<uint8_t>((s0 ? 1u : 0u) | (s1 ? 2u : 0u) | (s2 ? 4u : 0u));
}
void Hc4051::setEnabled(bool enabled) { enabled_ = enabled; }
bool Hc4051::connected() const { return enabled_; }
uint8_t Hc4051::selectedChannel() const { return selected_; }
uint16_t Hc4051::output() const { return enabled_ ? channels_[selected_] : 0; }

Hc165::Hc165()
    : parallel_(0), shift_(0), plHigh_(true), ceHigh_(false), serialIn_(false) {}
void Hc165::asyncLoadIfSelected() { if (!plHigh_) shift_ = parallel_; }
void Hc165::setParallelInputs(uint8_t value) { parallel_ = value; asyncLoadIfSelected(); }
void Hc165::setParallelLoadHigh(bool high) { plHigh_ = high; asyncLoadIfSelected(); }
void Hc165::setClockEnableHigh(bool high) { ceHigh_ = high; }
void Hc165::setSerialInput(bool high) { serialIn_ = high; }
void Hc165::clockRising() {
    if (!plHigh_) { shift_ = parallel_; return; }
    if (ceHigh_) return;
    shift_ = static_cast<uint8_t>((shift_ << 1) | (serialIn_ ? 1u : 0u));
}
bool Hc165::q7() const { return (shift_ & 0x80u) != 0; }
uint8_t Hc165::registerValue() const { return shift_; }

Stled316s::Stled316s() : readMask_(0), irq_(false), displayOn_(false) {
    key_[0] = key_[1] = 0;
    for (uint8_t i = 0; i < 7; ++i) display_[i] = 0;
}
void Stled316s::setKey(uint8_t keyRow, uint8_t scanColumn, bool pressed) {
    if (keyRow >= 2 || scanColumn >= 8) return;
    const uint8_t mask = static_cast<uint8_t>(1u << scanColumn);
    const uint8_t before = key_[keyRow];
    if (pressed) key_[keyRow] = static_cast<uint8_t>(key_[keyRow] | mask);
    else key_[keyRow] = static_cast<uint8_t>(key_[keyRow] & static_cast<uint8_t>(~mask));
    if (key_[keyRow] != before) {
        irq_ = true;
        readMask_ = 0;
    }
}
uint8_t Stled316s::keyByte(uint8_t keyRow) const { return keyRow < 2 ? key_[keyRow] : 0; }
uint8_t Stled316s::readKeyByte(uint8_t keyRow) {
    if (keyRow >= 2) return 0;
    readMask_ = static_cast<uint8_t>(readMask_ | static_cast<uint8_t>(1u << keyRow));
    if ((readMask_ & 0x03u) == 0x03u) irq_ = false;
    return key_[keyRow];
}
bool Stled316s::irqActiveLow() const { return irq_; }
void Stled316s::writeDisplayByte(uint8_t digit, uint8_t value) { if (digit < 7) display_[digit] = value; }
uint8_t Stled316s::displayByte(uint8_t digit) const { return digit < 7 ? display_[digit] : 0; }
void Stled316s::setDisplayOn(bool on) { displayOn_ = on; }
bool Stled316s::displayOn() const { return displayOn_; }

} // namespace virtualhw
} // namespace metro
