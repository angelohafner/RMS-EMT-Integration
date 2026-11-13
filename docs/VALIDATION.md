# Validation record — 13 November 2026

This is the original power-flow/EMT release record. The later native dynamic
extension is documented separately in [DYNAMIC_VALIDATION.md](DYNAMIC_VALIDATION.md)
and [DYNAMIC_MODEL.md](DYNAMIC_MODEL.md); its generated DYR supersedes the original
absence of a dynamic comparison for this demonstration.

This record describes **actual licensed simulator runs**, not example waveforms.
The release artifacts are `runs/release_capacitive`, `runs/release_inductive`
and `runs/release_timestep`. Other run folders in the working directory are
development evidence and are excluded from the delivery archive.

## Environment and execution

- PSS/E **35.6.4**, Python **3.11.4**, PSCAD **5.1.0**.
- Automation Library **3.1.2**; GFortran **13.2 (64-bit)**.
- Exact Python dependency closure: `requirements-tested.txt`.
- Both cases completed the normal CLI: PSS/E power flow/ASCC → JSON handover →
  native PSCAD project generation/build/run → native output processing → report.
- **15 offline tests passed**. These cover bases, complex-power orientation,
  RLC load equivalence, invalid inputs, waveform RMS/Q, malformed native files,
  altered result hashes, absent electrical faults and incomplete RMS coverage.
- **15/15 physical checks passed for each case**. The checks include actual
  fault resistance/current behavior and PCC power balance, not just logic signals.
- Source and engineering review findings were corrected; the final configurable
  labels come from the study data.

## Operating-point comparisons

| Initial condition | PSS/E PCC V (pu) | EMT pre-fault V (pu) | PSS/E Q (MVAr) | EMT Q (MVAr) |
|---|---:|---:|---:|---:|
| Capacitive | 1.017696261 | 1.017696259 | +20.000000 | +20.000004 |
| Inductive | 0.868674326 | 0.868674332 | −20.000000 | −19.999989 |

Comparison window: **0.80–0.95 s**. Both studies use the nominal ±100 MVAr device
rating, a **0.251021856 kA RMS** current limit, and a **1.00–1.15 s** three-phase
fault with 1 Ω per-phase fault resistance. Native fault channels confirm 150 ms.
The two initial conditions exercise both Q signs; they do not establish the full
physical capability curve of a manufacturer's STATCOM.

The source-only ASCC extraction gives nominal short-circuit level
**299.999989 MVA**, **SCR ≈ 3**, **R = 17.545822 Ω/phase**, and
**L = 0.465417413 H/phase**. Operating-point agreement is intentionally strong
because the EMT passive aggregate and terminal current are initialized to the
same solved P/Q; it is not independent dynamic model validation.

## Time-step sensitivity

The capacitive case was repeated with **2.5 µs**, against the released **5 µs**
integration step. Output sampling remained **20 µs**. Error metrics cover 0.8–2 s,
including the fault transitions; no event window was removed from this test.

| Quantity | RMSE | Maximum absolute difference | RMSE limit | Maximum limit |
|---|---:|---:|---:|---:|
| Voltage (pu) | 0.000261821 | 0.0123231 | 0.005 | 0.020 |
| STATCOM current (kA RMS) | 0.000006464 | 0.000062242 | 0.002 | 0.010 |
| STATCOM Q (MVAr) | 0.00986188 | 0.136992 | 1.0 | 5.0 |

All three predeclared numerical criteria passed. This is a two-step sensitivity
check of the reported cycle quantities, not an asymptotic convergence proof or
verification of sub-microsecond fault-current peaks. Machine-readable results
are in `runs/release_timestep/timestep_comparison.json`.

## Engineering limits and unavailable inputs

The explicit **100 nF/phase PCC capacitance** is a configurable illustrative input,
not a value extracted from PSS/E. The parallel inductor preserves the solved net
load Q. Earlier R–L-only and coarser-step trials did not adequately resolve the
clearing-voltage transient; they are not presented as the release results.

The ideal averaged terminal model has no PWM, DC-link energy balance, transformer
losses, PLL dynamics, surge arresters, blocking or protection. Its filtered angle
allows transient active-power exchange without a DC-energy constraint. The
capacitive run's maximum cycle voltage is about **1.519 pu**, maximum cycle Q
about **123.294 MVAr**, and maximum absolute cycle active power about **39.131 MW**.
Q can exceed the nominal-voltage MVAr rating during overvoltage while current
remains limited. These excursions characterize this unprotected terminal
surrogate, not equipment withstand, converter energy or synchronization limits.

**No equivalent PSS/E dynamic STATCOM model/DYR was supplied.** Dynamic RMS fault
comparison remains unavailable. The delivered tables compare real PSS/E power
flow with settled EMT only. Templates identify the matched DYR, DLLs, channels,
units and equivalence evidence needed to enable a genuine dynamic comparison.

The workflow is sequential and offline. It has no real-time coupling, synchronized
solver exchange or feedback of EMT results to PSS/E.
