# Evidence intake and wiring preflight, v0.4

This tool works only on local files. It never connects to a programmer, writes to the
module, launches original firmware, or attaches simavr GPIO. It closes a software gap:
previously any nonempty evidence string could justify a board assignment. Now every
assigned value needs a reviewed claim, a matching board identity and an existing,
SHA-256-checked artifact. Hashes establish byte integrity, not measurement truth.
Human review must establish that a file actually supports the claim.

Requires Python 3.9 or newer. Run commands from the project directory.

## Inspect the current state

```
python3 host/evidence.py status
python3 host/evidence.py plan --roles display.clock display.strobe display.data
```

Those role labels are an example naming convention, not rev010 pin assignments or
proof that these three signals suffice. The current map has zero verified connections,
so the second command reports missing roles and exits 2. Status exits 0 for a valid
but incomplete map. Malformed/inconsistent input exits 1. A ready requested subset
exits 0 but still reports `boardEmulated: false` and `originalFirmwareRunnable: false`.
Plans include map/registry hashes and all artifacts supporting the requested bindings.
Regenerate plans after any map, registry or artifact change; there is no runtime adapter
consuming old plans yet.

## Register a real measurement file

After following the read-only hardware worksheet, use a file you actually recorded:

```
python3 host/evidence.py register /absolute/path/to/measurement.txt --id session01-net01 --kind continuity --observed-at 2026-10-18T22:00:00+02:00 --operator "Your name" --notes "Describe the exact endpoints, instrument and unpowered test procedure"
```

Replace the example date and description with the actual observation. Supported kinds:
`continuity`, `pcb_trace`, `passive_capture`, `device_readout`.

The file is copied byte-for-byte under `evidence/local/`, hashed and registered with
`status: pending` and an empty claims list. The original is untouched. A repeated id or
existing destination is rejected. A local lock and atomic registry replacement protect
against competing intake writers. Manual edits must not run concurrently with intake.
After an interrupted process, inspect any lock/orphan file before removing it; the tool
does not guess whether an earlier writer is still active. This is not a transactional
backup system across sudden power loss.

## Review and record exact claims

Edit `specs/evidence-registry.json` only after inspecting the artifact. Add a claim:

```
{"pin":"<measured MCU physical pin>","fields":{"target_ic":"<observed board designator>","target_pin":"<measured IC pin or signal>"}}
```

Use actual string values, not these placeholders. Supported pin fields are `direction`,
`role`, `target_ic`, `target_pin`, `active_level`, `pull`, `analog_digital`, and
`interrupt_relevance`. Each assigned field requires evidence; leave unknowns null in
the map. Direction is from the MCU perspective: input/output/bidirectional.
Signal type is analog/digital. Other fields are nonempty descriptions.

A continuity reading generally supports endpoints, not active level, interrupt use or
operating direction. Do not add those claims without the corresponding evidence.
Use additional reviewed records for passive captures or other supporting observations.
The validator checks every assigned value, even on incomplete pin rows.

Set `status` to `reviewed`, add a nonempty `reviewer`, and an ISO 8601 `reviewed_at` with
timezone. The tool does not make this review decision. In `specs/hardware-map.yaml`,
copy the supported values into the exact physical pin row, reference the record id in
`evidence`, and set `confidence` and `verification` to `verified`. The file is JSON
syntax, despite its historical .yaml extension. Pin numbers are decimal strings.
Conflicting reviewed claims anywhere in the registry stop validation; resolve them
explicitly and retain the raw evidence. Do not silently choose one.

Metadata claims have the form `{"field":"clock_hz","value":<measured integer>}`.
Supported metadata fields: electronic_signature (lowercase six-digit hex string),
clock_hz (positive integer, at most 20,000,000), lock_bits (integer byte), and fuses
(object with low/high/extended integer bytes). Attach their ids in the map's
`metadata_evidence` slots. A measured identity mismatch blocks the target workflow.
Reading fuse bytes does not itself certify a clock frequency.

Finally run:

```
python3 scripts/validate-hardware-spec.py
python3 host/evidence.py status
```

## Scope of a wiring plan

A plan accepts only an explicitly requested set of unambiguous, fully described,
reviewed digital MCU bindings. Power/reference, reset/clock and analog routes are
rejected by this generic preflight. They need separate adapters and qualification.
No GPIO binding code is generated and no chip connection is guessed. Shared bus
fanout, hardwired supply ties and multiple endpoints per pin require a future netlist
schema; the existing single-target pin rows must not be overloaded to pretend otherwise.
Peripheral candidate contracts remain generic; real mappings live only in the map.

The synthetic tests create temporary invented records to exercise validator behavior.
They never enter the real registry and are not evidence about the physical board.
Generic peripheral tests are inherited abstractions, not complete wire-level models.

## Private data and packaging

`evidence/local/` is excluded from git and Docker build context. Keep original firmware
and hardware dumps local. A map that depends on excluded local evidence intentionally
fails validation in a clean container: mount/provide the private evidence explicitly
for a private workflow, or use the untouched public blank map. Do not remove evidence
requirements to make a container build pass. No measurement or firmware dump is included
in the v0.4 delivery. Never redistribute Intellijel firmware with future archives.
