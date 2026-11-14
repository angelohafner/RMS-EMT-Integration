# RMS-EMT integration: visual revision 1.1.0

## Authorized objective and current request

The existing 116-second English Manim film explains the validated sequential
PSS/E 35.6.4 to PSCAD 5.1.0 workflow. The user requested on 2026-11-14:
1. Remove the phasor equation/axis overlap.
2. Redraw the circuit with Schemdraw, balanced component proportions and a
   red fault resistor with a nearby lightning bolt.
3. Increase plotted sample density so the oscillations can be seen.

Keep English narration/captions, MathTex variables and plain Re()/Im(), real
simulation evidence, reproducible Python sources and public GitHub sync.
The user already authorized public repository creation and synchronization.

## Engineering boundary

- Sources: docs/DYNAMIC_MODEL.md and docs/DYNAMIC_VALIDATION.md.
- Native runs: runs/dynamic_capacitive_v2, runs/dynamic_inductive_v2 and
  runs/dynamic_timestep_v2. No new simulations are needed for this visual fix.
- Weak 230 kV grid, SCR approximately 3, nominal +/-100 MVAr averaged STATCOM;
  initial +20/-20 MVAr; 1 ohm/phase fault at 1.00-1.15 s.
- 15 RMS and 15 EMT physical checks per case, with recorded step refinements.
- Matched terminal controls have different transient network/angle behavior.
  Keep the material clearing-voltage difference visible. No PWM, DC-link
  energy model, full PLL or manufacturer protection. Sequential and offline,
  with no real-time exchange between the solvers.

## Existing release

- Repository: https://github.com/angelohafner/RMS-EMT-Integration
- Preserved release: video-v1.0.0, source commit
  0a65c622f5cada544587108991c57e5d3a2d58f7.
- Original movie/package/audits are also copied into video/output/v1.0.0/.
- Original licensed engineering archive remains
  delivery/RMS_EMT_STATCOM_Dynamic_v2.zip; SHA-256
  cfb5fd7157ef8d266d1d741299473764360ce17bb33048412006884b08f057b6.

## Revision decisions and progress

- Existing Guy Neural English narration and SRT remain unchanged.
- Phasor axes moved above a separate equation band.
- video/circuit.py now generates proportional IEEE components, aligned branches,
  fixed switch contacts, a red fault resistor and a Schemdraw lightning polygon.
  Coordinate metadata positions the MathTex labels consistently.
- Compact dataset replaced with every original row in 0.8-1.4 s: 30,001 samples
  per EMT curve and 1,202 per RMS curve. All 12 curves were independently checked
  against every source CSV row. No result values are synthesized.
- Result scene shows the fault overview followed by a 1.15-1.26 s time zoom;
  RMS curves are dashed to distinguish the closely tracking traces.
- Phasor/circuit/overview/zoom previews were visually checked; independent review
  verified all source samples and corrected the capacitor/highlight margin.
- Full-HD review caught Manim cache suppressing add_sound() after chapter 1.
  Final audio now comes from six original MP3s mixed by FFmpeg at absolute
  timeline offsets. The audit checks the complete stream and compares each
  decoded chapter against its original audio (correlation >=0.97).
- Transitions use whole-frame play durations and absolute chapter timing.
  Caption changes fade instead of morphing letters; the plot pointer is smaller.
- Final movie/audio audit passed: 116.132688 s, 1080p30, no decode errors.
  All 6 speech chapters present/aligned, source correlations >0.99998;
  mean audio -20.8 dB, peak -0.8 dB. All scene endpoints match their schedule.
- Final movie SHA-256: 4c77f2e155c4d626b171cbc1f2b54c2579231771fdd1971a7b478c97459d49c2.
- Final frames checked; independent closing review found no remaining blocker.
  It rechecked all six audio correlations and the final MP4 hash.
- Public release complete: https://github.com/angelohafner/RMS-EMT-Integration/releases/tag/video-v1.1.0
- Release source commit: 33059b443702b818e18c4dfd2a5c73e608052f3c.
- All 8 published assets verified by size and SHA-256 and read back publicly.
  The original video-v1.0.0 release remains published and unchanged.
- Editable ZIP: 90 files, all CRC/SHA checks passed; all 25 offline tests passed
  after extraction. Scene/circuit modules loaded in the documented video venv.
- Package SHA-256: 6ccb625fe0f4cf3f156187913eb02f0e3cd707c0e8f4491c389d9d805b42fdf5.
- Local version-specific video: video/output/RMS_EMT_Integration_EN_1080p_v1_1.mp4.
- Local version-specific editable package: video/output/RMS_EMT_Manim_Editable_v1_1.zip.
- The archive is the audited pre-publication source snapshot. This context and
  video/publication.json retain the completed publication record on main.
- Requested corrections, rendering, validation and publication are complete.
- Audio checks establish decoding, timing and levels; subjective listening is
  not certified. Real source samples do not remove one-cycle measurement filtering.

Read this file before resuming and update it at production/publication milestones.
