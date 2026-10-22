# Hardware discovery checklist — no writes

This package needs no physical module connection. Preserve the original MCU untouched.
Before a later readout session, identify programmer, voltage compatibility, header pin 1,
orientation and who powers the module. Do not combine power sources unintentionally.

1. Record module revision, chip marking, programmer model, firmware/tool versions,
   cable arrangement and photographs. Choose ATmega328 explicitly, not an Arduino profile.
2. Establish the electrical/power plan before attaching the programmer.
3. Read signature first. Stop on mismatch; never force a mismatched part identifier.
4. Read low/high/extended fuses and lock bits. Do not infer clock from an Arduino default.
5. Read EEPROM; read flash only when existing protection permits. Do not bypass locks.
6. Save logs, command arguments and timestamp; hash each raw dump. Read twice and compare
   bytes if a read is allowed and stable. Keep original and copies separate.
7. Stop. No chip erase, flash writes, fuse writes or lock changes during discovery.

No ready-to-run programmer command is supplied because programmer, port, supply and
header orientation are unknown. Read-only command review is a later hardware gate.
Required record: signature, fuse/lock bytes, tool/version, power, duration, output files,
SHA-256, read status and any error. A protected flash is a valid result, not a reason to erase.
