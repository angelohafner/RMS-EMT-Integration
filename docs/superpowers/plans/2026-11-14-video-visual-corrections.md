# Requested video visual corrections

User-approved scope: remove the phasor/equation overlap, redraw the circuit with
Schemdraw using proportional symbols, make the fault resistor red with a nearby
lightning bolt, and increase plotted sampling so oscillations are visible.

Implementation follows the existing Manim film and its recorded English speech.
No new simulations or synthesized result samples are required. The existing
public release remains available; publish the revision as video-v1.1.0.

- [x] `video/scenes.py`: place the phasor equation in a separate band beneath
  shorter axes; verify clear separation in a rendered frame.
- [x] `video/circuit.py`: generate consistent-sized IEEE resistors, inductors,
  capacitors, aligned branches, a red fault resistor and a red lightning symbol.
  Keep switch contacts and circuit bounds fixed in open/closed states. Export
  circuit coordinate metadata for MathTex labels in `scenes.py`.
- [x] `video/data_pipeline.py`: retain all original output samples over 0.8–1.4 s;
  verify every selected row and original source hash. Do not interpolate new data.
- [x] `video/scenes.py`: show the full fault overview followed by a 1.15–1.26 s
  clearing/recovery zoom. Use all available samples within each view.
- [x] Render changed chapters for visual review, then the 116-second Full HD film;
  check overlap, symbol proportions, red fault emphasis and visible recovery.
- [x] Audit decoding, audio/timing, sample counts and provenance; run relevant
  existing tests and independent review; package the updated editable project.
- [x] Update README, review record and CONTEXT; publish video-v1.1.0 and verify
  uploaded hashes and clean Git synchronization.
