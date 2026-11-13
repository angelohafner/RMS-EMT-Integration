# Prepared external SAV input contract

The runnable default generates its own SAV and PSCX. It needs no uploaded model.
For a different PSS/E case, set `psse.case_path` to an existing solved or solvable
SAV and identify `pcc_bus`, `grid_bus`, `boundary_circuit`, `load_id` and
`statcom_load_id`. Configure the actual frequency and PCC nominal voltage.

This adapter retains ONE PCC with one passive aggregate load and one STATCOM
represented as a negative Q load. The net retained injection must balance the
specified boundary branch. Prepare a one-port boundary; multiple interfaces,
PCC generation, additional shunts or different retained equipment require an
extended boundary adapter. Negative active-power STATCOM loads are not supported.
The saved case must contain valid sequence data; it is not inferred for real grids.

ASCC intentionally excludes ALL loads, line charging, shunts and FACTS when
calculating source impedance. This is a source-only, balanced positive-sequence
equivalent. Review this approximation for the intended study. Non-conventional
sources or MOVs need the newer `arrbox.fault` workflow and are unsupported here.
For networks with frequency-dependent impedance, unbalance or multiple ports,
this one-frequency R–L equivalent is insufficient.

The local passive load is converted to parallel R–L–C impedance at the operating
voltage. Supply `load.capacitance_nf` as a separately justified terminal-capacitance
input. The L branch is adjusted so the aggregate net Q still matches PSS/E.
If the full system's dynamics are important, a frozen Thévenin source cannot
replace them. This is sequential initialization and a local EMT study.

## Missing inputs for a detailed converter replacement

- Validated PSCX/PSLX, any runtime libraries, compiler requirements and license.
- Transformer ratio/leakage/loss/grounding, converter topology and ratings.
- DC-link voltage/capacitance, PWM strategy/frequency and switching devices.
- PLL, voltage/current controls, limiter priority, blocking, protections and restart.
- Component IDs/parameter names and units, measurement channels and orientations.
- Validated initialization procedure and comparison criteria.

No fictitious vendor PSCX or DYR is included. The generated averaged PSCX is a
complete runnable terminal model, not a placeholder for those missing details.
