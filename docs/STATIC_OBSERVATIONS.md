# Selected original-firmware static observations

Image: Metropolis 1.37 rev009+, HEX SHA-256
`996cac09c44112cccf7d89a50cdb600722586c1cd807536730134794dd9569c9`.
Analyzed locally with the pinned AVR binutils 2.26 package. Original code bytes and
disassembly are not included. These are candidate landmarks, not recovered symbols.

| Requested entry | Observed absolute CALL/JMP sites | Interpretation scope |
| --- | --- | --- |
| 0x0350 | 0x3f5e | Startup SPI transaction, PB2 select |
| 0x0394 | JMP at 0x1ee8 | SPI update path reached through an absolute tail jump |
| 0x03d2 | 0x456e | Repeated two-byte scan under PC5 |
| 0x06c0 | CALL at 0x3f1e, 0x3f3e; JMP at 0x4506 | GPIO serial output used during startup |
| 0x0752 | 0x4580 | GPIO read request and bidirectional-data turnaround |

Runtime write callbacks corroborate SPDR writes at 0x0366/0x036e/0x0376 and
0x03f4/0x03fe. The PC5 scan derives a command from a rotating 0..7 index multiplied
by eight, reads both returned bytes, and stores a word. The later PC4 path uses a
similar two-byte exchange. An ADC-like role is a hypothesis, not a component identity.

The 0x0752 path sends 0x49 LSB first, changes DDRB bit 3 to input, samples PINB bit 3
over two groups of eight clocks, and restores output direction. This agrees with a
STLED316S page-1/key-address-1 read request and its two key bytes. Actual returned key
state cannot be inferred from an unwired simulation's defaults.

`host/inspect_io_sites.py` reproduces an inventory of direct I/O access sites and
absolute callers to requested addresses. It does not construct a complete CFG:
linear disassembly may encounter data, and indirect or relative control flow is not
resolved. The address-only inventory is analysis support, not physical wiring evidence.
