# M1 lab interaction map

Pitch slider -> audition MIDI note; pulse selector -> 1–8; ratchet selector -> 1–4.
Skip removes duration; Rest mutes but preserves duration. Segment editor uses last stage
and repeat count; starts are inferred from the preceding boundary.
All edits stop and reset playback. Rejected configurations disable playback until fixed.
Transport uses a static C++ trace and WebAudio scheduling. Developer JSON is collapsible.

This is a lab editor, not a frozen physical panel. No gesture has been assigned to an
original button. Physical STAGES/button/encoder mapping and pickup remain M5 work.
