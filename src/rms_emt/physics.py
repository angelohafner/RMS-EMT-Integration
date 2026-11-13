"""Three-phase bases; phase-A RMS phasors; positive Q means injection."""
import cmath
import math


def impedance_from_strength(base_mva, short_circuit_mva, xr_ratio):
    if min(base_mva,short_circuit_mva,xr_ratio) <= 0:
        raise ValueError('MVA bases, short-circuit level and X/R must be positive.')
    r = base_mva / short_circuit_mva / math.sqrt(1+xr_ratio**2)
    return complex(r, r*xr_ratio)


def convert_operating_point(op, rating_mvar, capacitance_nf=0.):
    for key,value in op.items():
        if isinstance(value,(float,int)) and not math.isfinite(value):
            raise ValueError(f'Non-finite operating-point value: {key}')
    base,kv,f = (op[k] for k in ['base_mva','voltage_kv_ll','frequency_hz'])
    if min(base,kv,f,rating_mvar) <= 0:
        raise ValueError('Positive electrical bases are required.')
    v=complex(op['voltage_pu_real'],op['voltage_pu_imag'])
    z=complex(op['z1_pu_real'],op['z1_pu_imag'])
    if z.real < 0 or z.imag <= 0 or not .5 <= abs(v) <= 1.5:
        raise ValueError('Require passive inductive Z1 and a plausible operating voltage.')
    # Boundary power is positive from the external grid into the retained PCC.
    s=complex(op['boundary_p_mw'],op['boundary_q_mvar'])/base
    i=(s/v).conjugate()
    e=v+z*i
    zb=kv**2/base
    expected=complex(op['load_p_mw'],op['load_q_mvar']-op['statcom_q_mvar'])
    if abs(s*base-expected) > 0.01:
        raise ValueError('Boundary power does not balance retained load and STATCOM (0.01 MVA).')
    iq=op['statcom_q_mvar']/(rating_mvar*abs(v))
    if abs(iq) > 1.000001:
        raise ValueError('Operating point exceeds the rated current at the solved voltage.')
    if not math.isfinite(capacitance_nf) or capacitance_nf<0:
        raise ValueError('PCC capacitance must be finite and nonnegative.')
    vll=kv*abs(v)
    cap_f=capacitance_nf*1e-9
    cap_q=vll**2*2*math.pi*f*cap_f
    inductor_q=op['load_q_mvar']+cap_q
    return dict(schema_version=1, **op, z_base_ohm=zb,
                r_ohm=z.real*zb, x_ohm=z.imag*zb, l_h=z.imag*zb/(2*math.pi*f),
                e_pu_real=e.real,e_pu_imag=e.imag,
                source_kv_ll=abs(e)*kv,source_phase_deg=math.degrees(cmath.phase(e)),
                pcc_voltage_pu=abs(v),pcc_phase_deg=math.degrees(cmath.phase(v)),
                rated_current_ka=rating_mvar/(math.sqrt(3)*kv),iq_initial_pu=iq,
                grid_current_ka=abs(i)*base/(math.sqrt(3)*kv),
                short_circuit_mva_nominal=base/abs(z),scr=(base/abs(z))/rating_mvar,
                load_r_ohm=(vll**2/op['load_p_mw'] if op['load_p_mw']>0 else None),
                load_l_h=(vll**2/inductor_q/(2*math.pi*f) if inductor_q>0 else None),
                pcc_capacitance_f=cap_f,pcc_capacitor_q_mvar=cap_q,
                source_reconstruction_residual_pu=abs(e-z*i-v))
