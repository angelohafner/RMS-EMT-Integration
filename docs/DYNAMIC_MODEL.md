# Native PSS/E dynamic equivalent

The RMS extension uses PSS/E 35.6's built-in **SVSMO3T2**, attached to a FACTS
device named `STATCOM`. It generates a DYR file and a separate solved SAV, runs
the actual simulator, and preserves its OUTX. No external model DLL is required.
The original negative-Q load is disabled before adding the FACTS device, so its
injection is counted once. The original power-flow/EMT evidence is preserved.

## Controller mapping

Let `Iq0 = Q0/(Srating V0)`, with positive current producing capacitive Q. The
existing EMT command is `clip(Iq0 + (V0 - Vm)/droop, -1, +1)` followed by a current
lag. In SVSMO3T2 set:

| Parameter | Setting | Reason |
|---|---:|---|
| STBASE | 100 MVA by default | Same current base as EMT |
| Kp | 1/droop = 20 | Same proportional voltage/current law |
| KI | 0 | No active integral controller in EMT |
| Xc0 | 0 | Avoid adding an extra current-feedback droop loop |
| Tc1 / Tb1 | 0 / 0.010 s | Scalar voltage measurement lag |
| Tc2 / Tb2 | 0 / 0 s | Bypass extra lead/lag |
| T0 | 0.020 s | Same output-current lag |
| Imax1 / Ishrt | 1 / 1 | No short-term overload allowance |
| dbd / Kdbd | 0 / 0 | No deadband |
| MSS / slow reset / nonlinear droop | Disabled | Absent in EMT |
| UV2 / UV1 | 0 / 0.0001 pu | No blocking at the simulated fault voltage |
| OV1 / OV2 / Vtrip | 5 / 6 / 7 pu | Protection outside this demonstration's range |

These are matching settings for the ideal terminal demonstration, not proposed
equipment protection settings. Both signs use the same current limiter and base.

**Initialization detail matters:** Native initialization puts `Iq0` into the PI
integral state. The zero-KI native controller resets that state during saturation.
Leaving it there changes the final operating point after a fault. Therefore,
immediately after `strt_2`, the adapter makes the algebraically equivalent change
`Vref = Vscheduled = V0 + droop*Iq0` and zeros the inactive integral state,
derivative and integration memory with documented `change_state`. It applies
this transformation **once before RUN**, never during the trajectory. The
initialized snapshot retains it. The DYR alone does not encode this runtime
reference: use the supplied Python runner. `dynamic_powerflow.sav` is the
unconverted power-flow case; `initialized.snp` is retained as a diagnostic
snapshot. They are not advertised as a ready-made converted-SAV/SNP restart pair.
Native channels verify the state stays zero and the proportional law holds.

## Network, fault and channel conventions

- The source uses `GENCLS` with H=0 and D=0, holding its internal voltage and
  angle. The original generator source reactance and grid branch together give
  the transferred positive-sequence Thevenin impedance.
- The passive load is converted with `conl` to 100% constant admittance in P and
  Q. This equals the EMT parallel RLC load at the nominal frequency and solved
  voltage, but carries no electromagnetic storage states.
- The fault uses `dist_3phase_bus_fault(PCC, 0, 3, kV, [Rohm, 0])`; units=3 means
  ohms. It is cleared with `dist_clear_fault(1)`, without opening the grid branch.
  Requested times are 1.00 and 1.15 s; native `dsrval('TIME',0)` values are saved.
  `run_exact` approaches each boundary at the nominal step and uses one final
  partial step via `dynamics_solution_param_2` to land within 0.2 microseconds.
  It then restores the nominal step. This avoids single-precision TIME accumulation
  placing the fault a full integration step after the requested time.
- Voltage is the native bus-voltage channel. Signed current is SVSMO3T2 VAR(L)
  on STBASE; its magnitude is converted by `Srating/(sqrt(3)*Vbase)` to kA RMS.
- The model's Q VAR(L+2) can lag bus voltage during events. It is retained as
  `native_model_q_mvar`. Compared Q is computed from simultaneous native network
  FLOW1 channels: `Qinj = Q(PCC->grid) + Qload0*(V/V0)^2`. The fault is purely
  resistive and contributes no Q. A separate check requires agreement with
  `V*Iq*Srating`; fault active-power balance verifies the applied resistance.
- Native duplicate event times remain in OUTX and `native_channels.csv`. The main
  comparison CSV keeps the last value at an identical timestamp. Cycle integrals
  use both native pre/post-event samples, so the voltage jump has zero duration
  and is not smeared into the preceding time interval. Decreasing/nonfinite times
  are rejected. Metrics evaluate interpolated EMT data at native RMS sample times.

## Remaining differences

| Topic | PSS/E RMS | PSCAD EMT | Consequence |
|---|---|---|---|
| Network | Positive-sequence algebraic impedance | Three-phase RLC differential equations | RMS omits electromagnetic inception/clearing transients |
| Voltage measurement | Scalar magnitude, 10 ms lag | Filtered rotating-frame voltage vector | Equal small-signal timing at fixed angle; not identical under phase jumps |
| Current orientation | Reactive phasor relative to instantaneous bus voltage | Filtered angle, held below the voltage floor | Deep-sag current/Q and transient P can differ |
| Initialization | Starts at solved equilibrium | Energization, STATCOM enable at 0.3 s | Compare from the settled 0.8 s window |
| Reported measurements | Instantaneous phasor magnitudes and Q | Trailing one-cycle waveform RMS and Q | Event-inclusive errors contain measurement-window differences |
| Numerics | Configurable 0.5 ms RMS step by default | Released 5 microsecond EMT step | Each simulator needs its own time-step check |
| Converter detail | Averaged current-controlled terminal | Averaged current-controlled terminal | Neither includes PWM, DC-energy constraints, full PLL or manufacturer protection |

Reports include native-phasor metrics and one-cycle phasor-envelope metrics.
For the latter, V/I use square-root of the cycle mean of squared magnitude and Q
uses cycle mean. This aligns the reporting windows, not the physical models.
The full interval includes both switching events; separate windows help diagnose
steady behavior. Differences are descriptive results, not a claim of validated
manufacturer-model equivalence or hardware performance.

## Reproduce

```powershell
py -3.11 -m rms_emt.cli compare runs/release_capacitive --output runs/my_dynamic_capacitive
py -3.11 -m rms_emt.cli compare runs/release_inductive --output runs/my_dynamic_inductive
```

The command first verifies native EMT hashes, copies that evidence into a fresh
run, and executes native PSS/E dynamics in an isolated worker. Existing outputs
are never overwritten. To run every stage afresh, add `"rms": {"enabled": true,
"time_step_s": 0.0005}` to a configuration and use the normal `run` command.
This native adapter deliberately accepts the generated two-bus case only;
arbitrary external networks require their own dynamic models and initialization.

For the independent RMS numerical sensitivity check:

```powershell
py -3.11 tools/check_rms_timestep.py runs/my_dynamic_capacitive runs/my_rms_step_check
```

This reruns native RMS at half its step, retaining the same EMT evidence. The
declared criteria use cycle phasor envelopes over the full comparison interval,
including events; native phasor voltage itself is discontinuous at fault switching.

API/model sources: installed PSS/E 35.6.4 `ModelLibrary.pdf`, GENCLS p.27 and
SVSMO3T2 pp.749–752; `PAGV2.pdf` section 25.8.8; installed `API.pdf`/Python
docstrings for `facts_data_3`, `dyre_new`, `cong`, `conl`, `ordr`, `fact`, `tysl`,
`fcdmind`, `strt_2`, `change_state`, `change_fctmod_var`, `run`,
`dist_3phase_bus_fault`, `dist_clear_fault`, `dsrval`, channel APIs and `dyntools.CHNF`.
Proprietary manuals are not redistributed.
