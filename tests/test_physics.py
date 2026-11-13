import math
import pytest
from rms_emt.physics import convert_operating_point, impedance_from_strength
from rms_emt.config import load_config, validate_config


def operating_point():
    return dict(base_mva=100., voltage_kv_ll=230., frequency_hz=60.,
                voltage_pu_real=1., voltage_pu_imag=0.,
                z1_pu_real=0.02, z1_pu_imag=0.2,
                boundary_p_mw=30., boundary_q_mvar=-10.,
                load_p_mw=30., load_q_mvar=10., statcom_q_mvar=20.)


def test_bases_and_source_reconstruction():
    p = convert_operating_point(operating_point(),100.)
    assert p['z_base_ohm'] == pytest.approx(529.)
    assert p['r_ohm'] == pytest.approx(10.58)
    assert p['l_h'] == pytest.approx(105.8/(2*math.pi*60))
    assert p['rated_current_ka'] == pytest.approx(100/(math.sqrt(3)*230))
    # I = conj((0.3-j0.1)/1); E = 1 + (0.02+j0.2)*(0.3+j0.1).
    assert p['e_pu_real'] == pytest.approx(.986)
    assert p['e_pu_imag'] == pytest.approx(.062)


def test_strength_is_three_phase_nominal_base():
    z = impedance_from_strength(100,300,10)
    assert abs(z) == pytest.approx(1/3)
    assert z.imag/z.real == pytest.approx(10)


def test_parallel_rlc_preserves_net_prefault_load_power():
    op=operating_point();p=convert_operating_point(op,100.,100.)
    v2=230.**2
    ql=v2/(2*math.pi*60*p['load_l_h'])
    qc=v2*2*math.pi*60*p['pcc_capacitance_f']
    assert ql-qc==pytest.approx(op['load_q_mvar'])
    assert v2/p['load_r_ohm']==pytest.approx(op['load_p_mw'])


@pytest.mark.parametrize('key,value',[('frequency_hz',0),('z1_pu_imag',-1),('voltage_pu_real',float('nan'))])
def test_reject_nonphysical_point(key,value):
    op=operating_point();op[key]=value
    with pytest.raises(ValueError): convert_operating_point(op,100)


def test_configuration_rejects_too_early_fault_and_bad_sampling():
    c=load_config('config/demo.json')
    c['fault']['start_s']=0.1
    with pytest.raises(ValueError): validate_config(c)
    c=load_config('config/demo.json')
    c['simulation']['sample_step_us']+=c['simulation']['time_step_us']/2
    with pytest.raises(ValueError): validate_config(c)
