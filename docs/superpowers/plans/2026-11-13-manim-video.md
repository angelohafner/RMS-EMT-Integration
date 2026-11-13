# RMS–EMT Manim film implementation plan

> Execute inline using executing-plans; request an independent review of the film/source before final publication.

**Goal:** Execute the user's approved prompt: a narrated 90–120 s English Full HD
Manim film, Schemdraw circuits, MathTex variables with Re()/Im(), real results,
editable package, subtitles, persistent context and a new public GitHub repo.

**Architecture:** Isolated video environment. `data_pipeline.py` verifies source
hashes and extracts real channels and Schemdraw SVG. Narration/timings drive six
Manim scenes. FFmpeg assembles the scenes, audio and subtitles. An audit checks
duration, dimensions, timestamps, data provenance and content. Publish after QA.

**Constraints:** Preserve all simulation evidence. Label illustrative phasor
animation as conceptual. No invented waveforms presented as results. Explain
scalar versus dq filtering, RLC energy and measurement windows. No co-simulation
claim. The user has explicitly authorized public GitHub creation/synchronization.

- [x] Prepare isolated video dependencies and test narration availability.
- [x] Create script/timing, Schemdraw circuit and verified compact datasets.
- [x] Build six MathTex/Manim scenes with synchronized English narration.
- [x] Render Full HD, subtitles and editable package; audit actual frames/audio.
- [x] Independent engineering/visual review and corrections.
- [x] Create public repository, commit/push, publish video/package, verify remote.
- [x] Update CONTEXT.md and deliver final links.
