# Preset format reservation

Not implemented. Do not serialize raw C++ structs (padding/ABI differs across targets).
Reserve an explicit byte format with magic, schema, bounded payload length and CRC.
Validate into temporary state before committing. EEPROM allocation, migration and
power-loss behavior need separate tests. No EEPROM writes in this milestone.
