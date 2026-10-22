# Controlled input observations, v0.9.0

## Conditions and method

Original Metropolis 1.37, hash-pinned as before. Synthetic 16 MHz / 5 V, all-FF initial EEPROM, simulator default fuses and shared 328/P model. Each run starts fresh. Key pulses set one raw bit at cycle 22M and release it at 24M. Each single-channel test sets one synthetic 16-bit word to 512 from startup, leaving all other words zero.

Two independent stop points: 23.5M cycles (during the pulse) and 30M cycles (after release). Each captures a complete final 0.5M-cycle window. Every case is run twice with tracing and once without; the traced reports repeat exactly and their CPU/fixture reports match the untraced run. Complete key frames and SPI word pairs are checked against expected CPU input. Partial boundary frames are excluded or explicitly marked.

The matrix has four input scenarios × two status models × two timing profiles × two stops = 32 cases / 96 runs. The input sweep has neutral + 16 raw key bits + 16 channels, using master-divider at both stops = 66 cases / 198 runs. Total: 98 cases / 294 controlled runs, plus two unwired baseline checks. The matrix also preserves all four archived v0.8 trace hashes.

## Separating status from timing

All 16 matched status-model comparisons have equal final display pages and equal CPU receive-word sets. This shows the register corrections preserve these observed original-firmware paths; the synthetic CPU tests establish the corrected edge cases separately. The original firmware uses polling in these experiments, with zero SPI ISR entries and zero write collisions.

Timing changes final display pages in three of eight scenario/stop pairs, under either status model: channel-ramp at 23.5M and 30M, and combined channel-ramp/key-pulse at 23.5M. Input values received by the CPU are still the same. Faster polling/scanning is observable, but the cause of the differing higher-level display behavior is unresolved.

| Scenario at 30M | Fixed 100 us display page 0 | Divider timing display page 0 | SPI replies, fixed / divider |
|---|---|---|---|
| neutral | `39 3f 00 20 00 00` | `39 3f 00 20 00 00` | 4606 / 17404 |
| channel-ramp | `39 3f 00 08 07 00` | `39 3f 00 20 00 00` | 4629 / 17476 |
| key-pulse | `7c 73 06 5b 3f 00` | `7c 73 06 5b 3f 00` | 4620 / 17451 |
| channel-ramp-key-pulse | `7c 73 06 5b 3f 00` | `7c 73 06 5b 3f 00` | 4635 / 17512 |

## One raw key bit at a time

All 16 key words reach the CPU while active. No key test changes display page values relative to neutral at 23.5M. At 30M, 13 bits change display page values; bits 4, 14 and 15 do not. This does not prove those three bits are unused, nor that a blank display is a failure. The two observations do not locate the exact time of the change or prove release-triggered handling.

Neutral display page 0 at 30M is `39 3f 00 20 00 00`. Bytes below are observed display RAM, not verified glyphs, physical button names or musical functions.

| Raw bit | Returned 16-bit key word while active | Page 0 at 30M | Changed vs neutral |
|---|---|---|---|
| 0 | `0x0001` | `7c 73 06 5b 3f 00` | yes |
| 1 | `0x0002` | `6d 76 00 6d 3f 00` | yes |
| 2 | `0x0004` | `00 00 00 00 00 00` | yes |
| 3 | `0x0008` | `00 00 00 00 00 00` | yes |
| 4 | `0x0010` | `39 3f 00 20 00 00` | no |
| 5 | `0x0020` | `00 00 00 00 00 00` | yes |
| 6 | `0x0040` | `00 00 00 00 00 00` | yes |
| 7 | `0x0080` | `00 00 00 00 00 00` | yes |
| 8 | `0x0100` | `71 50 5e 00 00 00` | yes |
| 9 | `0x0200` | `6d 31 77 3f 7f 00` | yes |
| 10 | `0x0400` | `6d 31 79 73 06 00` | yes |
| 11 | `0x0800` | `39 76 50 3f 55 00` | yes |
| 12 | `0x1000` | `00 00 00 00 00 00` | yes |
| 13 | `0x2000` | `39 3f 00 00 00 00` | yes |
| 14 | `0x4000` | `39 3f 00 20 00 00` | no |
| 15 | `0x8000` | `39 3f 00 20 00 00` | no |

Bit 13 additionally changes display-driver page 1 from `00` to `08`. Pages 2 and 3 remain the same in these experiments. A physical LED assignment is not established.

## One synthetic channel at a time

For PC5 and PC4, channels 0 through 7 each have an independent case with value 512 and all other channels zero. Every case confirms complete CPU reads containing both zero and 512 on the selected bank, and only zero on the other bank. The full fixture counter also records requests by channel.

None of these 16 single-channel cases changes final display pages or the set of captured six-byte display payloads at either stop. This is a bounded negative observation, not proof of disconnected or ignored controls. The firmware may consume these inputs elsewhere, the synthetic packing/pipeline may be wrong, or the observed mode/windows may not expose their effects.

SPI channel identity, resolution, alignment, conversion latency and pipelining remain hypotheses. A real ADC/device model must not be inferred solely from the two-byte reply adapter.

## Interpretation limits and next step

All new-model original runs record three unanswered startup transfers and three unread RX overwrites, zero collisions, zero ignored non-master writes, zero aborted transfers and at most one cycle of timer lateness. The unserved PB2 startup path remains unidentified. No analog CV/gate output or physical waveform is measured.

The evidence supports a raw input-to-display observation table and a timing-sensitive channel discrepancy. Next work should isolate channel packing/pipeline and compare the relevant firmware input-consumption behavior before assigning panel controls or presenting this as a working Metropolis front panel.

Full compact records: artifacts/spi-behavior-matrix.json and artifacts/spi-behavior-sweep.json. Regenerate with scripts/verify-spi-behavior.py --suite matrix and --suite sweep. Raw traces remain excluded under firmware-local/behavior-analysis. No original firmware or disassembly is included.
