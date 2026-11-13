# Native dynamic STATCOM comparison implementation plan

> Execute inline using executing-plans; review the completed extension independently.

**Goal:** Add a real PSS/E SVSMO3T2 run using the existing solved operating point and compare voltage, STATCOM current and Q with the genuine EMT output.

**Architecture / design:** Preserve the original release runs. A new `compare` command verifies and copies an existing run, replaces the static negative-Q load by a native FACTS device in a separate PSS/E process, loads generated GENCLS/SVSMO3T2 DYR records, runs the same resistive PCC fault, exports native channels, then generates a comparison report. The normal `run` command can also enable this stage. No fabricated curves or Python surrogate solver.

**Model choice:** The installed ModelLibrary 35.6.4 pp. 749–752 documents SVSMO3T2. Use its proportional controller (Kp=1/droop, Ki=0), constant initialized bias, no additional current-droop feedback (Xc0=0), 10 ms measurement lag, 20 ms output lag, and ±1 pu current limit. Disable slow reset/MSS/nonlinear droop. Put protection thresholds outside the simulated range, explicitly as an ideal-model matching choice. Verify native initialization and actual current/Q behavior. If zero Ki is unsupported, revise the mapping from observed/documented evidence rather than label a mismatched PI equivalent.

**Alternatives considered:** CSTCNT adds transformer/internal-voltage and integrator dynamics absent from the EMT model. A custom DLL would add a compiler/toolchain dependency without necessity. Native SVSMO3T2 is the best existing supported terminal-model match.

**Limits:** Positive-sequence algebraic RLC impedance differs from EMT electromagnetic storage; scalar voltage filtering differs from the EMT dq vector filter/angle hold; instantaneous phasor channels differ from trailing-cycle waveform measures; initialized RMS excludes EMT startup. Document these and include event-inclusive metrics as well as settled windows. No equipment validation claim.

**Constraints:** PSS/E 35.6, Python 3.11, genuine OUT/OUTX, documented APIs, 230 kV base, 1 ohm per phase fault at 1.00–1.15 s by default. Preserve all old evidence and archives. This workspace is not a Git repository; no worktree/commit is applicable.

## Tasks and review focus

- [x] Add parameter mapping and tests for gain/base/sign, state/limit placement, configuration and event-step alignment.
- [x] Add native RMS worker: FACTS power-flow replacement, GENCLS source, constant-impedance load, DYR, fault, native channels, physical checks, hashes and failure handling. Inspect actual initialization log, current limits and voltage sag.
- [x] Extend CLI/reporting for verified copied EMT evidence, native provenance, monotonic channels with event duplicate handling, full-event and windowed metrics, honest model-difference table.
- [x] Run both capacitive/inductive cases, halve the RMS integration step, run offline tests and review plots; retain failures as development evidence only.
- [x] Independent engineering/code review; address substantive findings, document actual results and create a separate v2 archive with hash verification.

## Execution ledger

- Design decision: proceed with native SVSMO3T2 based on the user's explicit request to add/run the equivalent dynamics; no additional approval is needed for this reversible extension.
- Read installed vendor model block diagram and API docstrings; no proprietary manual content will be redistributed.
- Ruling from native probe: the Ki=0 integrator is reset on saturation, so transfer Iq0 to Vscheduled/Vref and zero STATE/DSTATE/STORE once before RUN. The resulting native output returns to the original operating point and the command law is checked throughout the comparison interval.
- Ruling from native probe: model Q VAR is lagged relative to bus voltage at events. Preserve it separately; compare simultaneous native FLOW1 balance Q and verify against V*Iq*Srating. Native OUTX is unchanged.
- Reports explicitly include event-inclusive and separate-window metrics; an optional cycle-envelope comparison does not remove electromagnetic model differences.
- First 0.5/0.25 ms numerical check failed the voltage maximum criterion (0.13629 pu). Evidence showed a 0.204 ms difference in actual event timestamps plus artificial interpolation across the native voltage jump. Retain that failed development evidence. Final revisions use native final partial-step event alignment and preserve both event samples for discontinuous integration; re-run both cases and the unchanged numerical criteria.

Final validation: v2 native events align within 0.024 microseconds; two cases pass 15 RMS + 15 EMT checks; 24 tests pass. Unchanged RMS refinement criteria all pass (max V 0.000339909 pu, I 0.000209727 kA, Q 0.110098 MVAr). Review findings fixed and tested. Final evidence excludes development probes.
