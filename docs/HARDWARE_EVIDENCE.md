# rev010 evidence dossier — 2026-10-18

All six original photos were visually inspected in this implementation session.
Images are observations, not a schematic or proof of electrical connections.

| Image suffix | Observation | Confidence / limit |
|---|---|---|
| 7302807 | METROPOLIS Main rev010 silkscreen, IC12 socket and ICSP label | High; header orientation not established |
| 7501505 | IC12 marking ATMEGA328-PU, DIP socket | High; not ATmega328P; electronic signature unread |
| 7516654 | STLED316… marking visible | Family high confidence; exact package suffix and routing unverified |
| 7524442 | IC1 HC165AG marking visible | New shift-register-family candidate; role and connections unknown |
| 7542896 | 74HC4051D marking, analog area and additional ICs | Mux family high confidence; channels unknown |
| 7552107 | Analog/support area, trimmer and several ICs | No output topology inferred from placement |

Full filenames retain `image-179232` prefix in `evidence/hardware_images/`.
No component role has been promoted to a verified MCU pin connection.
The `hardware-map.yaml` placeholders deliberately contain no guessed signal mapping.

Source handoff archive SHA-256:
5df7f228a685e015a86a954139dde85a4f2f06f0c92348065cccfe31a869c339
The supplied ten-file handoff manifest matched before work began.
