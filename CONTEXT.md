# RMSâ€“EMT integration: active video production

## Authorized objective

Produce a 90â€“120 second Full HD Manim film explaining the validated sequential
PSS/Eâ€“PSCAD workflow. All on-screen variables/equations use LaTeX MathTex with
plain `Re()` / `Im()` (`operatorname`), never stylized real/imaginary symbols.
Use Schemdraw circuits. English text, subtitles and an enthusiastic English
narrator. Create a public GitHub repository and synchronize the project.

## Engineering sources

- `docs/DYNAMIC_VALIDATION.md` and `docs/DYNAMIC_MODEL.md`.
- `runs/dynamic_capacitive_v2`, `runs/dynamic_inductive_v2`.
- `runs/dynamic_timestep_v2/rms_timestep_comparison.json`.
- Native PSS/E 35.6.4 and PSCAD 5.1.0 evidence: 24 offline tests; 15 RMS and
  15 EMT physical checks per case; both numerical refinements passed.
- 230 kV, SCR approximately 3; nominal Â±100 MVAr averaged terminal STATCOM;
  initial +20 / âˆ’20 MVAr; 1 ohm/phase fault at 1.00â€“1.15 s.
- RMS/EMT control settings are matched, not identical transient models.
  The EMT clearing-voltage transient remains materially different. No DC-link
  energy model, PWM, manufacturer protection or full PLL. No real-time coupling.

## Production decisions

- Six narrated chapters: concept; phasors/waveforms; operating point and transfer;
  circuit and fault; measured comparison; limitations and reproducibility.
- Use the existing verified simulation data; no new solver runs are required.
- Production files live under `video/`; separate Python environment uses installed
  Manim 0.21.0 and isolated video dependencies.
- Narration will be generated before animation timing; retain audio, script,
  timing and subtitles. Final output must contain audible synchronized narration.
- GitHub owner verified via connector: `angelohafner`. Connector has no repository
  creation action, so use the official GitHub API for creation and Git for sync.
- Publish project source and generated demonstration assets. Exclude local vendor
  manual extracts, development trials, caches, environments and credentials.

## Progress / next actions

- Source validation record and toolchain inspected; Manim, FFmpeg and LaTeX exist.
- English narration generated: Microsoft Guy Neural (passionate voice), +5% rate, +2 Hz pitch.
- Six chapters total 116.13 s; word-timed English SRT exists.
- Verified data reduction preserves extrema; Schemdraw open/closed circuits created.
- Preview rendered and inspected; circuit labels and switch animation corrected.
- Full HD movie rendered and audited: 116.099 s, 1920x1080, 30 fps; audio mean -23.8 dB / peak -3.9 dB; no decode errors.
- Data hashes and displayed extrema verified; 25 offline tests pass.
- Independent review found no material engineering/visual issue. Corrected the optional install command to target Python 3.11 explicitly.
- Public repository created: https://github.com/angelohafner/RMS-EMT-Integration
- Final movie: video/output/RMS_EMT_Integration_EN_1080p.mp4
- Editable package: video/output/RMS_EMT_Manim_Editable.zip
- The video includes synthetic English narration, actual simulation comparisons, and optional English captions.
- Full-file decoding/timing/levels and sampled visual frames were checked; subjective listening was not certified.
- Public release completed: https://github.com/angelohafner/RMS-EMT-Integration/releases/tag/video-v1.0.0
- Release source commit: 0a65c622f5cada544587108991c57e5d3a2d58f7 (tag video-v1.0.0).
- Eight release assets verified by remote SHA-256 and size, then read back without authentication. Details: video/publication.json.
- Editable ZIP: 84 files, CRC and all file hashes verified; all 25 tests pass after extraction and the packaged Manim scene loads.
- Movie SHA-256: 4cf74e7dd9870b5dcbda146f295e6412c79740044b26a08e7a008b041a1b561a.
- Package SHA-256: 55b06d5c7d4285524094a743589ed1cfb0704a3ddeda5056a459a6b57a60d9d9.
- All requested production and publication work is complete. The release archive is a frozen pre-publication source snapshot; this file and video/publication.json record the completed publication.
- Main includes the release sources plus this final publication record. Use git status/log and origin/main to inspect the current synchronized revision.
- GitHub publication uses existing authenticated access; credentials are never included in artifacts.

Read this file before resuming. Update it after each meaningful milestone and
record the final repository URL, commit, artifact paths and remaining limitations.
