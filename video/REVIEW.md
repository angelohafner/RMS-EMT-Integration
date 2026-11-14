# Video revision 1.1.0: review and verification

The user requested correction of the phasor equation overlap, a professional
Schemdraw circuit with proportional symbols and a red fault resistor/lightning
bolt, and more plot samples to reveal oscillations.

## Delivered corrections

- The phasor equation occupies its own band below the complete axis extent.
- Schemdraw IEEE resistors have reduced body length and zigzag width, matching
  the scale of the inductors/capacitor. Branches and labels use common geometry.
- The fault resistor, switch and lightning polygon are red. The open/closed
  switch uses fixed contacts; the drawing bounds are identical in both states.
- The active-fault highlight clears the capacitor label by 0.1505 Manim units
  and the lightning bolt by 0.3394 units (independently measured).
- Every original row over 0.8–1.4 s is retained: 30,001 points per EMT curve and
  1,202 per RMS curve. All 12 time/value arrays exactly match the source CSVs.
- The clearing/recovery zoom (1.15–1.26 s) uses 5,501 EMT and 220 RMS points per
  curve. RMS is dashed. No interpolated or smoothed display samples are added.
- Text changes fade sequentially to avoid overlapping/morphing glyphs; the peak
  pointer is small enough to leave the voltage transient visible.

## Final audiovisual checks

The final MP4 is **116.132688 s, 1920 × 1080, 30 fps**. The complete
file decodes without errors. Audio duration is **116.132688 s**;
mean level is -20.8 dB and peak level is -0.8 dB.
English SRT and an optional English subtitle track are included.

The six original English MP3 files and timeline are unchanged from version 1.0.
During revision review, a Manim cache issue was found: cached animations could
suppress add_sound() after the first chapter. The finalizer now assembles all
speech clips with FFmpeg at their absolute timeline offsets, independently of
Manim audio. It checks actual stream duration and compares decoded audio in
**each of the six chapters** with the corresponding original speech. All six
correlations exceed **0.999990**;
the acceptance threshold is 0.97. A single narrated chapter cannot pass this check.

Whole-frame animation durations and static waits prevent cumulative timing drift.
The six recorded scene endpoints match the requested timeline within floating-point
precision; see render_timing.json. MP4 container rounding is below one millisecond.

Source hashes match the preserved native engineering release. The audit checks
actual dataset minima/maxima and complete sample counts. The existing offline
suite passes all 25 tests. These tests do not replace licensed simulator evidence.

## Review scope and limits

Changed chapter previews and nine final Full HD frames were inspected, including
open/closed fault states and the overview/zoom plots. Independent review covered
layout bounds, all source rows, packaging dependencies and the final audio path.
Original engineering results, faults, control settings and comparisons are unchanged.

More samples and the zoom reveal the available recovery detail; they do not undo
the one-cycle measurement filtering or increase the native RMS simulation rate.
The introductory phasor/sine animation remains labeled conceptual. The actual
comparison plots retain the material clearing-voltage difference. Integration
is sequential and offline, with the model limitations stated in the film/docs.

Audio identity/timing checks do not certify subjective pronunciation or perceived
enthusiasm. Original speech files are included for direct listening. The original
video-v1.0.0 release and its local archived outputs remain available.
