# Released video review

The delivered film is `RMS_EMT_Integration_EN_1080p.mp4`: 116.099349 s,
1920 × 1080, 30 fps, H.264 video, AAC English narration, optional English
subtitle track plus a separate SRT. See `audit.json` for the file hash and checks.

## Technical and visual evidence

- FFmpeg decoded the entire final file with no errors. Mean audio level is
  −23.8 dB and peak level is −3.9 dB; the final spoken chapter fits the movie.
- The six chapters total 116.133333 s before container rounding. Actual recorded
  speech and word timestamps drive chapter durations and subtitles.
- Every compact dataset/source CSV hash matches the released engineering
  manifest. Display reduction retains the original interval minima/maxima.
  An independent reviewer also matched all 12 display arrays to actual CSV rows.
- The capacitive voltage/current/reactive-power plots use one-cycle windows in
  both domains; 0.8–1.4 s includes inception and clearing. The full engineering
  comparison reports 0.8–2.0 s and both initial reactive-power signs.
- Nine extracted Full HD frames were reviewed across all six chapters. Circuit
  labels were moved clear of symbols. The fault branch changes from open to the
  Schemdraw normally-closed contact symbol during the highlighted interval.
- Electrical symbols and equations use MathTex; real and imaginary functions
  use upright `Re()` / `Im()` operators. All prose and captions are English.
- The full offline suite passes: 25 tests. These tests do not substitute for
  the separately recorded licensed simulator runs and physical checks.
- The editable ZIP passed CRC and every per-file SHA-256 check. All 25 tests
  also passed after extracting it into a separate directory.

## Independent review and corrections

An independent read-only review covered equations, model differences, source
hashes, curve samples/extrema, chapter/audio timing, extracted frames and rebuild
instructions. It identified an ambiguous Python command in the optional data
re-extraction instructions. That command now explicitly uses the Python 3.11
video environment. The compact engineering manifest is a required finalizer
input and is included in both the source repository and editable archive.

The apparent crossed blade in the closed circuit was checked against Schemdraw
0.23 source: it is the library's normally-closed contact-line convention, not an
open fault branch. No material engineering or visual issue remained in scope.

## Review limits

Audio checks establish non-silence, level, successful decoding and timing.
They do not certify subjective pronunciation or perceived enthusiasm. The voice
was selected from the service's passionate-personality metadata and configured
with +5% rate and +2 Hz pitch; no separate expressive-style parameter is applied.
The actual MP3s are included for direct listening. Rendering was verified in
the stated Windows environment; other computers need the documented packages,
FFmpeg, LaTeX/dvisvgm and font setup.

The introductory sine wave is a labeled concept illustration. All plotted
simulation comparisons are real licensed results. The film retains the material
clearing-voltage difference and does not claim manufacturer-model validation,
switching fidelity, full PLL/DC-energy behavior or real-time co-simulation.
