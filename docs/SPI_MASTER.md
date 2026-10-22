# AVR master register profile, v0.9.0

## Run it

```sh
sh scripts/build-inspector.sh
python3 host/inspect_firmware.py firmware-local/metropolis_1.37.hex \
  --runner build/cpu_inspector --cycles 30000000 \
  --fixture specs/fixtures/key-pulse.json \
  --trace-limit 100000 --trace-start 29500000 \
  --spi-status avr-master-v1 --spi-timing avr-divider-v1
```

Both options are explicit. Omitting them retains the prior native simavr behavior.

| Status option | Timing option | Behavior |
|---|---|---|
| omitted | omitted | Original simavr 1.6, fixed 100 us |
| omitted | avr-divider-v1 | v0.8 timer adapter, native register behavior |
| avr-master-v1 | omitted | New register model with fixed 100 us for controlled comparisons |
| avr-master-v1 | avr-divider-v1 | New register model with 8 configured SCK periods per byte |

This separates timing effects from register-model effects. Fixed 100 us in the new model is an experimental control, not an AVR timing claim.

## Register contract

The new implementation is in sim/spi_master.c. It installs before the response fixture and passive trace observer, and restores callbacks in reverse order. It saves the native register handlers and reuses the native SPI interrupt vector and output byte notification. It does not patch the installed simavr library.

| Operation | Qualified behavior |
|---|---|
| SPDR write while enabled master and idle | Latch TX byte and divider, begin one transfer; retain previous RX byte |
| SPDR write while busy | Set WCOL; reject new byte; preserve original TX and deadline |
| Transfer completion | Obtain explicit synthetic reply, replace RX buffer, set SPIF and request SPI interrupt if enabled |
| SPDR read | Return retained RX byte; repeated reads return the same byte |
| SPSR read | Return SPIF/WCOL/SPI2X, zero reserved bits; arm acknowledgement for flags observed set |
| Next SPDR read or write | Clear the armed flags; clearing SPIF also cancels its pending interrupt |
| SPSR write | Modify only SPI2X; preserve read-only SPIF/WCOL and zero reserved bits |
| SPI interrupt entry | simavr clears SPIF; WCOL remains until its acknowledgement sequence |
| SPIE enabled with SPIF already set | Request pending interrupt |
| New completion before previous RX is read | Replace RX and count unreadOverwrites |

Sources are the Microchip ATmega328P datasheet 7810D, sections 18.2 and 18.5, and simavr 1.6 interrupt implementation. Exact URLs and source hash are in artifacts/spi-master-sources.json. The simulator shares its 328/P model; these references do not prove the clock/fuses or behavior of the user's physical board.

The acknowledgement mask remembers flags seen set in SPSR until SPDR access. Ordinary polling, collision acknowledgement and interrupt-entry clearing are tested. Silicon-level races involving a new completion between status and data access are not independently qualified.

## Reply path and fixture integration

The profile emits SPI_IRQ_OUTPUT at byte completion. A response fixture replies synchronously through spi_master_receive, not native SPI_IRQ_INPUT. Native input notifications raise SPIF immediately, which would bypass the new completion/receive-buffer contract. Replies outside the completion window or multiple replies fail explicitly.

Unanswered transfers receive synthetic zero and are counted. This is not a floating-line model. Native SPI_IRQ_INPUT is not a supported input route for this optional profile. The bounded inspector only attaches its explicit fixture API. PB2's unidentified peripheral remains unserved.

A rejected busy write does not replace the fixture's pending chip-select/command state. Disabling SPE or leaving master mode cancels a pending model transfer and clears the fixture's pending transaction. That abort policy is explicit and tested for recovery; electrical behavior during mode changes is outside the qualified subset.

## Report fields

spiMaster contains writes, starts, completions, collisions, ignoredNonMasterWrites, abortedTransfers, unansweredTransfers, unreadOverwrites, statusReads, dataReads, spifAccessClears, isrEntries, maxCallbackLatenessCycles, pendingAtStop, receiveByte and configurationCounts. Counts cover the whole run, whereas trace analyses cover only their declared window.

configurationCounts uses [normal /4, /16, /64, /128, double /2, /8, /32, /64]. Divider selection is latched on accepted SPDR write. Timer callbacks run at instruction boundaries and may be late. The report's selected timing makes fixed-delay comparisons distinguishable.

SPI output trace callbacks occur before RX is latched and SPIF is raised by the new profile. Their SPSR snapshot is therefore not a post-completion status read. CPU SPSR/SPDR reads and ISR tests establish the register behavior. The passive observer does not add status reads.

## Tests and scope

Seventeen CPU integration tests execute small synthetic AVR programs, checking outcomes through actual register reads, byte callbacks and interrupts. They include all eight divider settings at two CPU frequencies and both timing options; SPIF acknowledgement versus premature status reads; retained RX across repeated reads and the next transfer; read-only status flags; collisions and original deadline preservation; new collisions after acknowledgement; receive overwrite; abort/recovery; late interrupt enable; ISR SPIF clearing with WCOL retained; and cancellation of an acknowledged pending interrupt. Every integration run is compared with an untraced run.

Four analysis tests separately check complete key frames, exclusion of partial windows, display values versus repeated write counts, and SPI word-boundary validation.

This remains a master byte/register model. Slave operation, electrical SCK/MOSI/MISO, SS-driven mode switching, PRR/CLKPR, oscillator/fuses, clock phase edges, asynchronous external replies, hardware reset/reinitialization and analog circuitry are not implemented. The runner installs the model once per process. Disabled/slave SPDR writes are counted and do not initiate master transfers. Mid-transfer mode changes are excluded from original-image acceptance, where those counters must remain zero.
