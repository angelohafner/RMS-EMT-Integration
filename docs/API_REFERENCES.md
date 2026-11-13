# API references and engineering conventions

Verified against installed PSS/E **35.6.4**, Python **3.11**, PSCAD **5.1.0** and
`mhi.pscad` **3.1.2**. API documentation was inspected before implementation;
local vendor manuals are not redistributed.

## PSS/E primary documentation

Installed manual: `C:/Program Files/PTI/PSSE35/35.6/DOCS/API.pdf`.
Python API functions also provide detailed docstrings in the installed package.
The official minor-version bootstrap is
`C:/Program Files/PTI/PSSE35/35.6/PSSPY311/psse3506.py`.

| Purpose | Actual API |
|---|---|
| Initialize/finish | `psspy.psseinit`, `psspy.pssehalt_2` |
| New/load/save case | `newcase_2`, `case`, `save` |
| Network data | `bus_data_4`, `plant_data_4`, `machine_data_2`, `branch_data_3`, `load_data_6` |
| Sequence data | `newseq`, `seq_machine_data_3`, `seq_branch_data_3` |
| Solve/check | `solution_parameters_5(realar6=...)`, `fnsl`, `solved` |
| Measurements | `sysmva`, `busdat`, `brnflo`, `loddt2` |
| Short circuit | `bsys`, `short_circuit_units`, `short_circuit_coordinates`, `short_circuit_z_units`, `short_circuit_z_coordinates`, `pssarrays.ascc_currents` |
| Read dynamics output | `dyntools.CHNF(...).get_data()` |
| Native STATCOM | `facts_data_3`, `dyre_new` with `SVSMO3T2` and `GENCLS` |
| Dynamic network conversion | `cong`, `conl`, `ordr`, `fact`, `tysl` |
| Dynamic controls/initialization | `dynamics_solution_param_2`, `fcdmind`, `strt_2`, `change_state`, `change_fctmod_var`, `snap` |
| Fault execution | `run`, `dist_3phase_bus_fault` (units=3, ohms), `dist_clear_fault`, `dsrval` |
| Native dynamic channels | `voltage_channel`, `var_channel`, `state_channel`, `branch_p_and_q_channel` |

For the native model equations, initialization transformation and measurement
conventions, see [DYNAMIC_MODEL.md](DYNAMIC_MODEL.md). The installed
`ModelLibrary.pdf` documents GENCLS p.27 and SVSMO3T2 pp.749–752.

`machine_data_2` and `seq_machine_data_3` are documented compatibility APIs in
35.6 (implemented internally through their newer versions). They are not invented
interfaces. Every nonzero PSS/E error code is treated as a failure, including
negative warning codes from data-entry calls.

The `ascc_currents` return object contains `ierr`, `fltbus`, `thevzpu[i].z1`,
`flt3ph[i].ia1`, `scunit`, `scfmt` and `scfmt_z`. Current and impedance are
explicitly requested in rectangular per-unit form. Current conversion uses the
case MVA and bus kV bases; no physical-unit assumption is made about raw ASCC data.

## PSCAD primary documentation

- [Launch and connection API](https://www.pscad.com/webhelp-v502-al/reference/launching.html)
- [Project parameters, run, messages and output](https://www.pscad.com/webhelp-v502-al/reference/project.html)
- [Canvas component creation](https://www.pscad.com/webhelp-v502-al/reference/canvas.html)
- [Component ports and parameters](https://www.pscad.com/webhelp-v502-al/reference/component.html)
- [Component Wizard](https://www.pscad.com/webhelp-v502-al/reference/wizard.html)
- [PSCAD 5.1 node-based current injection interface](https://www.pscad.com/webhelp-pscad-v5.1.0-ol/EMTDC/Custom_Model_Design/Node_Based_%28GGIN%29_Electric_Interface.htm)
- [PSCAD 5.1 intrinsic variables](https://www.pscad.com/webhelp-pscad-v5.1.0-ol/EMTDC/Custom_Model_Design/internal_global_variables.htm)

The online Automation Library pages are a published reference version, not a
claim that PSCAD 5.2 was used. Signatures and master-library parameter names were
also checked against the installed 5.1.0 library and 3.1.2 Python source. The build
uses `launch`, `licensed`, `setting_range`, `settings`, `create_case`,
`canvas.create_component`, `create_wire`, `Component.port/ports`,
`UserDefnWizard`, `project.parameters`, `save`, `run`, `messages`, `output`,
`temp_folder` and `quit`. `project.run()` is blocking; a parent worker timeout
bounds it. Component parameter names come from the installed `master.pslx`.

PSCAD's `time_step` and `sample_step` project parameters are in **microseconds**;
duration and fault times are in seconds. Electrical network units are kV, kA,
ohms and henries. The custom model uses documented `ENABCCIN` initialization, `CCIN` additive current
injection and `STORF` state storage; source currents are positive from ground into
the PCC. The output is native ASCII `INF` plus numbered `OUT` parts (10 channels
per part). Binary PSOUT is deliberately not silently parsed as ASCII.

## Equations and limitations

For three-phase MVA and line-line RMS kV:

```
Zbase[ohm] = VLL[kV]^2 / Sbase[MVA]
Ibase[kA]  = Sbase[MVA] / (sqrt(3) VLL[kV])
R[ohm]    = real(Z1[pu]) Zbase
L[H]      = imag(Z1[pu]) Zbase / (2 pi f[Hz])
Iport[pu] = conjugate((Pport+j Qport)/Sbase / Vpcc[pu])
Eth[pu]   = Vpcc[pu] + Z1[pu] Iport[pu]
SCR       = (Sbase/abs(Z1[pu])) / STATCOM_rating[MVA]
```

Pport and Qport are measured **into** the retained local system. STATCOM Q is
positive **injected into** the PCC. Thus Qport = Qload − Qstatcom. The parallel
load branches are R=VLL_operating²/Pload, Qc=2πf C VLL_operating² and
L=VLL_operating²/[2πf (Qload+Qc)]. Thus their net initial Q remains Qload.
The default 100 nF per-phase shunt capacitance is an explicit illustrative
terminal-capacitance input, not an extracted PSS/E parameter or equipment datum.
It supplies a finite energy-storage path during fault clearing; omitting all
capacitance produces a poorly resolved impulsive clearing voltage in this model.
The master-library `capacitor.C` parameter is expressed in **µF**, so Python
converts its stored farad value to an explicit `[uF]` parameter string.

The STATCOM uses `iq_target = clip(iq_initial + (V_operating − V_measured)/droop,
-1, 1)` followed by an exact first-order discrete update. Iq is rated-current
per unit. Its balanced current vector is 90 degrees behind the filtered voltage
vector, giving positive reactive injection. The phase estimate is held below
the voltage floor and continues at nominal frequency; this is ideal frequency
tracking, not a PLL. The electrical solution's one-step phase delay is compensated
at nominal frequency. During deep faults Q capability decreases with voltage.
The filtered angle can differ from the instantaneous voltage angle during a
transient, allowing active power exchange without a DC-energy constraint. This
is an ideal terminal surrogate, not an energy-conserving converter model. Q can
temporarily exceed 100 MVAr above nominal voltage while current remains limited.
Startup is excluded from comparisons. A one-frequency R–L equivalent omits
external network electromechanical and frequency-dependent behavior.
