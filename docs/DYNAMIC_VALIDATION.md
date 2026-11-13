# Native RMS–EMT dynamic comparison — validation record

Actual PSS/E **35.6.4** SVSMO3T2/GENCLS simulations were run for both +20 and −20 MVAr initial operating points of the nominal **±100 MVAr** device. They are compared with the previously executed, hash-verified PSCAD **5.1.0** EMT runs; the EMT curves were neither synthesized nor rerun for this extension.

Final evidence: `runs/dynamic_capacitive_v2`, `runs/dynamic_inductive_v2` and `runs/dynamic_timestep_v2`. Native DYR, SAV, diagnostic SNP, OUTX, event records, derived channels and provenance are included. **24 offline tests passed**, and each operating-point comparison passed **15 RMS and 15 EMT physical checks**.

## Fault and operating points

The same 1 Ω/phase three-phase PCC fault was commanded at 1.00 s for 150 ms. Both nominal-step cases and the refined case applied it at **1.000000000 s** and cleared it at **1.149999976 s**. Recorded duration is **149.999976 ms** (within 0.024 microseconds of the request). No line is tripped.

| Case | Native RMS pre-fault V (pu) | EMT V (pu) | Native RMS Q (MVAr) | EMT Q (MVAr) |
|---|---:|---:|---:|---:|
| Capacitive | 1.017696023 | 1.017696259 | +19.999921 | +20.000004 |
| Inductive | 0.868674338 | 0.868674332 | -20.000002 | -19.999989 |

Comparison window for initial conditions: 0.80–0.95 s. Both runs return to the initial operating point following clearing.

## Dynamic comparison results

The following metrics compare one-cycle RMS phasor envelopes with EMT one-cycle waveform measurements over **0.8–2.0 s**, including inception and clearing. Evaluation uses native RMS sample times and interpolated EMT values. No event window is discarded. The full CSV/HTML also reports unfiltered native-phasor metrics and separate time windows.

| Case | Quantity | Unit | RMSE | Maximum absolute difference |
|---|---|---|---:|---:|
| Capacitive | Voltage | pu | 0.0442088 | 0.662881 |
| Capacitive | Current | kA RMS | 0.00137016 | 0.0131496 |
| Capacitive | Reactive power | MVAr | 0.887472 | 10.9329 |
| Inductive | Voltage | pu | 0.0321272 | 0.529263 |
| Inductive | Current | kA RMS | 0.00140693 | 0.01346 |
| Inductive | Reactive power | MVAr | 0.879719 | 7.63535 |

Current and Q track closely after measurement alignment, but **the clearing-voltage difference remains material**. In the capacitive case, native RMS phasor voltage peaks at approximately **1.2674 pu**, while EMT one-cycle RMS reaches **1.5186 pu**. These are different measurement definitions; the aligned metrics above still show a substantial voltage difference. The EMT RLC network contains energy-storage transients absent from the RMS algebraic network. Filtered dq angle tracking/low-voltage angle hold in EMT also differs from instantaneous reactive phasor orientation in RMS.

The terminal controls are matched in proportional gain, voltage-filter time constant, output-current lag and current limit. This is a bounded engineering equivalent, **not identical transient models or manufacturer-model validation**. Neither model contains PWM, DC-link energy limits, a full PLL or equipment protection. The illustrative 100 nF/phase EMT capacitance is retained from the original study. See [DYNAMIC_MODEL.md](DYNAMIC_MODEL.md) for equations, initialization and all remaining differences.

## Independent RMS time-step check

The capacitive case was repeated at **0.25 ms**, against the released nominal **0.5 ms** RMS step. Final partial steps align events precisely. Cycle integrals retain duplicate native pre/post-event samples and do not spread a voltage jump across an earlier interval. The same limits were declared before running; all pass over 0.8–2 s, including events.

| Quantity | RMSE | Maximum difference | RMSE limit | Maximum limit |
|---|---:|---:|---:|---:|
| v_pu | 3.76553167e-05 | 0.000339909316 | 0.005 | 0.03 |
| i_ka | 2.77457199e-05 | 0.000209726997 | 0.001 | 0.005 |
| q_mvar | 0.012932864 | 0.110098178 | 0.5 | 3 |

This is a two-step check of the reported cycle envelopes, not an asymptotic convergence proof. The earlier development check failed its voltage criterion because of event-time drift and interpolation across discontinuities; it prompted the final corrections above. That failed development run is excluded from the release archive. The original EMT 5-to-2.5 microsecond check remains documented in [VALIDATION.md](VALIDATION.md).

## Reproduction and review

Use `config/demo_dynamic.json` or `config/demo_dynamic_inductive.json` with the normal `run` command for a fresh full chain. Use `compare` to add native RMS to an existing verified EMT run. The runtime bias-to-reference initialization transformation is required; DYR alone does not reproduce it. The saved power-flow SAV is unconverted and the SNP is diagnostic; use the Python runner for supported replay.

Independent review covered the native model mapping, event handling, power/current units, provenance, measurement windows and configuration-dependent checks. An analytical discontinuity regression, slower-controller regression and altered/unregistered-output tests passed. Figures were visually inspected. Exact file hashes are provided in the archive manifest.

Integration remains **sequential and offline**. There is no real-time exchange, synchronized solver coupling or EMT feedback into the RMS dynamics.
