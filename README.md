# Sequential PSS/E–PSCAD STATCOM demonstration

Python builds a PSS/E **35.6** case, solves power flow, extracts an ASCC
positive-sequence Thévenin equivalent, transfers it to **PSCAD 5.1.0**, creates a
native EMT case, runs it, and produces technical figures, comparison tables and
an HTML report. **This is sequential, offline integration, not real-time
co-simulation.** PSCAD runs after PSS/E finishes; no feedback crosses the boundary.

Actual execution evidence: [original validation record](docs/VALIDATION.md) and
[native dynamic validation](docs/DYNAMIC_VALIDATION.md).

**Narrated Manim film:** [watch/download the 116-second Full HD video and editable
package](https://github.com/angelohafner/RMS-EMT-Integration/releases/tag/video-v1.0.0).
The [video instructions](video/README.md) include independent rendering without
simulator licenses. English narration, captions, Schemdraw circuits and MathTex
variables are included. [CONTEXT.md](CONTEXT.md) preserves the project decisions.

The release also contains `RMS_EMT_STATCOM_Dynamic_v2.zip` with the actual native
runs and their SHA-256 manifest. Extract its `RMS_EMT_STATCOM/runs/` directory
into this project root to use the existing-run commands below. These large
native outputs are release assets, not Git history.

The native dynamic extension is documented in [DYNAMIC_MODEL.md](docs/DYNAMIC_MODEL.md).
Run `py -3.11 -m rms_emt.cli compare runs/release_capacitive --output runs/my_dynamic`
to add a genuine SVSMO3T2 PSS/E fault run to verified EMT evidence. This generates
native DYR/SAV/SNP/OUTX files and voltage/current/Q overlays. Both current signs
are supported; no external model DLL is needed.

Latest dynamic results: [capacitive report](docs/results/capacitive/report.html),
[inductive report](docs/results/inductive/report.html), and
[dynamic validation record](docs/DYNAMIC_VALIDATION.md).
To regenerate the entire chain (new power flow, new EMT, new RMS), run:

```powershell
py -3.11 -m rms_emt.cli run --config config/demo_dynamic.json
py -3.11 -m rms_emt.cli run --config config/demo_dynamic_inductive.json
```

The default study is a **230 kV, 60 Hz, SCR=3 grid**, a **±100 MVAr nominal
averaged STATCOM terminal model**, and a three-phase PCC fault from **1.00 to
1.15 s**, with **1 Ω per phase**. No simulation files are required for this default:
the actual `.sav` and `.pscx` are generated using vendor APIs.

The STATCOM is a transparent current-limited reactive injection with voltage
droop and first-order current response. It does **not** include PWM, DC-link
energy, PLL dynamics or a manufacturer's controls. See [model scope](docs/design.md)
and [equations/API references](docs/API_REFERENCES.md) before adapting it.

## Requirements and installation

- Windows, licensed PSS/E 35.6 with Python 3.11 support.
- Licensed PSCAD 5.1.0 and a working Fortran/C compiler combination.
- Python **3.11 64-bit**, not the system-default Python 3.14.
- The run uses a **new PSCAD instance**. The configured user profile is loaded
  for its license settings; the user's already-open projects are not edited.

From this project folder in PowerShell:

```powershell
py -3.11 -m pip install -e ".[pscad,test]"
py -3.11 -m rms_emt.cli doctor --config config/demo.json
py -3.11 -m rms_emt.cli validate --config config/demo.json
py -3.11 -m pytest -q
py -3.11 -m rms_emt.cli run --config config/demo.json
```

For the exact tested Python package versions, install `requirements-tested.txt`
before the editable project: `py -3.11 -m pip install -r requirements-tested.txt`.

PSS/E's `psspy` and `pssarrays` come from its licensed installation, **not pip**.
Edit `psse.python_path` and `pscad.compiler` in `config/demo.json` for your machine.
The documented test environment uses GFortran 13.2 (64-bit). The offline tests do
not require either simulator and do not constitute simulator validation.

Each run gets a new `runs/<UTC timestamp>_<id>/` directory. An explicit output
directory can be selected with `--output runs/my_run`; it must not already exist.
Licensing can take several minutes on this machine. The default per-worker
timeout is 600 s. Logs are written while each worker runs.
PSCAD compilation is staged automatically in an ASCII temporary directory,
because its native compiler path handling can fail on Unicode workspace names.
The finished PSCX and raw outputs are copied back. To run a generated PSCX
manually in PSCAD, first copy it to an ASCII path.

## Outputs

| Artifact inside a run | Purpose |
|---|---|
| `config.json`, `manifest.json` | Frozen configuration, stage status and validation outcome |
| `psse/solved.sav` | Actual solved PSS/E case with sequence data |
| `psse/operating_point.json` | P/Q/V, Z1, converted R/L, source E, units, bases and provenance |
| `psse/psse.log`, `*_worker.log` | Solver messages and worker errors |
| `pscad/StatcomEMT.pscx` | Generated native PSCAD schematic and transparent controller |
| `pscad/raw/*.inf`, `*.out` | Actual native EMTDC output, never synthetic fallback traces |
| `pscad/provenance.json` | Versions, compiler and input/output SHA-256 hashes |
| `report/report.html` | Self-contained technical report with embedded plots |
| `report/overview.png/.svg`, `waveforms.png/.svg` | RMS/power overview and instantaneous fault waveforms |
| `report/comparison.csv`, `emt_processed.csv` | Pre-fault comparison and processed time series |
| `report/checks.json`, `metrics.json` | Machine-readable physical checks and summary values |
| `rms/statcom.dyr`, `dynamic_powerflow.sav`, `initialized.snp` | Native dynamic model, unconverted power-flow case and diagnostic snapshot |
| `rms/dynamics.outx`, `native_channels.csv`, `channels.csv` | Native output, duplicate-preserving channels and normalized channels |
| `rms/events.json`, `metadata.json` | Requested/actual event times and RMS provenance |
| `report/dynamic_comparison.csv`, `aligned_overview.png/.svg` | Native-phasor/cycle-envelope comparison metrics and event-detail plot |
| `report/rms_checks.json` | Recalculated native RMS physical checks |

To regenerate a report from existing native output:

```powershell
py -3.11 -m rms_emt.cli report runs/my_run
```

Failed stages return a nonzero exit code and retain their diagnostics. A report
with failed checks is marked **FAIL**, not silently accepted. Startup is excluded
from pre-fault comparison. Current is positive STATCOM injection; positive Q
means capacitive support. The current limit is 100/(√3×230) = **0.251022 kA RMS**.
At low voltage, the model cannot maintain 100 MVAr while respecting this limit.

## Configuration and comparisons

Grid strength, X/R, P/Q load, initial STATCOM Q, droop, response time, fault time,
fault resistance and integration/output steps are configurable. The default
5 µs integration step and 20 µs output step are different settings. PSS/E's
negative-Q load represents the STATCOM's power-flow operating point only.
The EMT load is a parallel R–L–C aggregate matching the solved net P/Q at that
voltage. Its explicit default **100 nF per-phase terminal capacitance** is an
illustrative engineering input, not extracted or measured equipment data. The
inductor is adjusted to keep the original net Q. This finite capacitance is
necessary to represent the fast clearing transient; it is not a DC-link capacitor.

The default comparison is **PSS/E power flow versus settled pre-fault EMT**.
Without the optional native RMS stage or supplied dynamic channels, the original
run has no dynamic fault comparison. Enable the new native stage with
`"rms": {"enabled": true, "time_step_s": 0.0005}` or use `compare` above.
A power-flow result is never plotted as a dynamic fault response.

If you have an equivalent PSS/E dynamic study:

1. Supply its real OUT/OUTX, matching DYR and any model DLLs.
2. Fill explicit channel numbers and unit/sign multipliers in a copy of
   `templates/rms_channels.json`.
3. Export with `py -3.11 tools/export_psse_channels.py mapping.json rms.csv`.
4. Complete `templates/rms_metadata.json`, including file hashes and an engineering
   assessment of network, load, controls, limits, initialization and fault equivalence.
5. Set `comparison.rms_csv` and `comparison.rms_metadata`. Comparisons use
   overlapping data and include the complete fault interval. Separate pre-fault,
   fault-interior and post-fault windows distinguish transient effects. Both
   native-phasor and cycle-envelope metrics are reported because trailing-cycle
   EMT measurements differ from instantaneous phasor magnitudes.

The workflow does not assume an arbitrary vendor STATCOM DYR matches the averaged
EMT model. See [external case and missing-input contract](templates/external_case.md)
for real-system SAV inputs or a detailed converter replacement.

## Modules and stage commands

`config.py` validates inputs; `physics.py` handles bases and source reconstruction;
`psse_worker.py` owns PSS/E; `pscad_model.py` builds the native model;
`pscad_worker.py` owns PSCAD; `results.py` processes native signals;
`reporting.py` produces evidence; `cli.py` orchestrates isolated processes.

For diagnosis, use fresh stage directories:

```powershell
py -3.11 -m rms_emt.psse_worker config/demo.json runs/manual/psse
py -3.11 -m rms_emt.pscad_worker config/demo.json runs/manual/psse/operating_point.json runs/manual/pscad
```

Use the main CLI for normal operation: it adds timeouts, a configuration snapshot,
status manifests and validation. An installed compiler or simulator version alone
does not establish that a license, build or run succeeded; inspect the actual run
manifest and report.

An inductive initial-condition variant is available in `config/demo_inductive.json`
(-20 MVAr initially, same ±100 MVAr nominal rating and fault). To assess the
clearing transient's numerical sensitivity after a successful baseline run:

```powershell
py -3.11 tools/check_timestep.py runs/my_run runs/my_step_check
```

This reuses the verified PSS/E handover and halves only the EMT integration step.
Its fixed error thresholds and actual results are saved in
`timestep_comparison.json`. Step convergence does not validate the omitted
converter energy, controls or protection.
