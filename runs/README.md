# Native PSS/E and PSCAD cases

The repository includes all 58 native model files present in the local study
on 2026-11-14: 18 PSCAD `.pscx`, 24 PSS/E `.sav`, 8 `.dyr` and 8 `.snp` files.
Their original paths and bytes are preserved. The 141 accompanying JSON files
record configurations, operating points, events, provenance and existing checks.
The [file manifest](../docs/NATIVE_MODELS_MANIFEST.json) lists sizes, SHA-256
hashes and Git blob hashes for these 199 files.

## Current dynamic cases

| Case | PSCAD schematic | PSS/E power flow | Dynamic inputs |
|---|---|---|---|
| Capacitive, +20 MVAr initially | [StatcomEMT.pscx](dynamic_capacitive_v2/pscad/StatcomEMT.pscx) | [solved.sav](dynamic_capacitive_v2/psse/solved.sav) | [rms/](dynamic_capacitive_v2/rms/) |
| Inductive, -20 MVAr initially | [StatcomEMT.pscx](dynamic_inductive_v2/pscad/StatcomEMT.pscx) | [solved.sav](dynamic_inductive_v2/psse/solved.sav) | [rms/](dynamic_inductive_v2/rms/) |
| Time-step refinement | [StatcomEMT.pscx](dynamic_timestep_v2/pscad/StatcomEMT.pscx) | [solved.sav](dynamic_timestep_v2/psse/solved.sav) | [rms/](dynamic_timestep_v2/rms/) |

Each current `rms/` directory contains `statcom.dyr`, `dynamic_powerflow.sav`
and `initialized.snp`. The SAV is the unconverted dynamic power-flow case;
the SNP is the recorded diagnostic snapshot. Use the documented Python
workflow for initialization and event execution. PSS/E 35.6 and PSCAD 5.1
with their licenses are required. No external PSS/E model DLL is required.
Copy a PSCAD case to an ASCII-only path before compiling it manually.

## Earlier study stages

The `development*`, `validated_*`, `final_*`, `release_*`, `dynamic_probe2`,
`rms_probe1`, `timestep_check` and dynamic folders without the `_v2` suffix
preserve earlier stages. They may contain partial or superseded cases. Their
publication does not certify a new simulation or make them the current study.
Existing manifests and check files retain their original status; see
[DYNAMIC_VALIDATION.md](../docs/DYNAMIC_VALIDATION.md) for the accepted results.

## Complete output traces

Git contains the model inputs and small supporting records. Native output
traces, generated Fortran, logs and full reports remain outside Git. Download
`RMS_EMT_STATCOM_Dynamic_v2.zip` from the
[published release](https://github.com/angelohafner/RMS-EMT-Integration/releases/tag/video-v1.1.0)
for the complete accepted runs. Extract `RMS_EMT_STATCOM/runs/` into the project
root before regenerating reports from existing outputs. The original receipts
also reference these release-only outputs.

Synchronization verifies file identity; it does not rerun either simulator.
