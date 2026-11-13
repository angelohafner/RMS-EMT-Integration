# Sequential RMS–EMT demonstration

The authorized deliverable is a reproducible Python workflow for PSS/E 35.6 and
PSCAD 5.1.0, with a 230 kV weak grid, a ±100 MVAr STATCOM and a 150 ms fault.
This is an offline, one-way handover of a solved operating point and a frozen
positive-sequence network equivalent. There is no real-time exchange or iterative
feedback between solvers.

## Engineering choices

The default is a transparent, averaged STATCOM terminal model constructed by the
PSCAD Automation Library. It is a controlled three-phase reactive current source
with voltage droop, a first-order current response and a rated current limit.
This is suitable for demonstrating network handover and voltage support. It does
not model PWM, a DC capacitor, converter losses, PLL loss of synchronism, protection,
or a manufacturer's control. A vendor switching model would require missing
equipment data and cannot be claimed equivalent to this model.

A configurable two-bus PSS/E case is generated with documented data APIs. A
balanced external-grid ASCC calculation supplies positive-sequence impedance.
The local load and STATCOM are excluded from the impedance calculation; the
STATCOM is represented by a negative reactive load in power flow. The grid source
behind the extracted impedance is reconstructed from the boundary current.
Physical units, sign conventions, bases and model assumptions travel in JSON.

PSCAD contains physical R–L grid branches, passive R–L–C load branches, a timed
three-phase shunt fault and the averaged current injection. Its instantaneous
voltage and current outputs are processed into trailing one-cycle RMS and power.
Power-flow comparisons use settled pre-fault EMT quantities. The optional native
SVSMO3T2 extension now generates a dynamic PSS/E case and channel metadata; see
[DYNAMIC_MODEL.md](DYNAMIC_MODEL.md). Supplied equivalent dynamic channels are
also supported. Without either source, dynamic comparison is explicitly unavailable.

An explicit illustrative terminal capacitance of 100 nF per phase completes the
local R–L–C aggregate. Its inductor is adjusted to preserve the solved net Q.
This capacitance is an additional configurable engineering input; PSS/E does not
identify it. The released integration step is 5 microseconds and output interval
20 microseconds, with a separate half-step sensitivity check. High clearing
overvoltages and transient active power remain limitations of the unprotected
ideal terminal surrogate, not predictions of a physical STATCOM.

Alternatives considered: adapting the installed switching STATCOM example would
require undocumented retuning and rating assumptions; using an unverified vendor
model would obscure the demo. The averaged terminal model is the implementation
choice, with its scope clearly stated in every report.

## Validation and delivery

Test conversion, complex-power signs, short-circuit base, current limiting,
waveform processing and stale/malformed-file rejection. Run both installed
simulators when licensed. Record exact versions, configuration, checksums, logs,
raw outputs, figures, comparison tables and an HTML report. Failed or unavailable
stages never generate substitute simulation traces. Unit-test signals remain
inside tests. An external-case template identifies required boundary and model
inputs. Timeout/error paths produce actionable diagnostics.
