"""Tests for RMS/EMT model mapping and non-fabricated native channel processing."""
import json
from pathlib import Path
import numpy as np
import pytest


def test_native_controller_matches_static_gain_and_time_constants():
    from rms_emt.dynamic import model_parameters
    c=json.loads(Path('config/demo.json').read_text())
    p=model_parameters(c)
    assert p['Kp']==20 and p['KI']==0 and p['Xc0']==0
    assert p['Tb1']==.01 and p['T0']==.02
    assert p['Imax1']==1 and p['Ishrt']==1 and p['STBASE']==100
    assert p['UV2']<p['UV1']<.005 and p['OV2']>p['OV1']>2


def test_duplicate_native_events_keep_post_event_sample():
    from rms_emt.dynamic import normalize_channels
    a=normalize_channels([0,.1,.1,.2],[1,1,.01,.02],[.2,.2,.3,.4],[20,20,.3,.8],100,230)
    assert list(a['time_s'])==[0,.1,.2]
    assert a['v_pu'][1]==.01
    assert a['i_ka'][1]==pytest.approx(.3*100/(np.sqrt(3)*230))
    assert a['q_mvar'][1]==.3


def test_decreasing_native_time_is_rejected():
    from rms_emt.dynamic import normalize_channels
    with pytest.raises(ValueError,match='time'):
        normalize_channels([0,.2,.1],[1,1,1],[0,0,0],[0,0,0],100,230)


def test_rms_step_must_land_on_fault_events():
    from rms_emt.dynamic import validate_rms_settings
    c=json.loads(Path('config/demo.json').read_text())
    c['rms']={'enabled':True,'time_step_s':.0003}
    with pytest.raises(ValueError,match='event'):
        validate_rms_settings(c)


def test_bias_is_moved_into_reference_without_changing_initial_command():
    from rms_emt.dynamic import controller_initialization
    c=json.loads(Path('config/demo.json').read_text())
    op={'statcom_q_mvar':-20.,'pcc_voltage_pu':.87}
    s=controller_initialization(c,op)
    assert s['integrator_bias_pu']==0
    assert (s['voltage_reference_pu']-.87)/.05==pytest.approx(-20/(100*.87))


def test_current_response_check_accepts_configured_slower_inductive_lag():
    from rms_emt.dynamic import current_lag_residual
    t=np.arange(0,.151,.0005);tau=.04
    iq=1+(-.230235879-1)*np.exp(-t/tau)
    assert current_lag_residual(t,iq,np.ones(len(t)),tau)<1e-12
    assert current_lag_residual(t,np.full(len(t),iq[0]),np.ones(len(t)),tau)>.9


def test_cycle_integral_preserves_native_duplicate_time_jump():
    from rms_emt.dynamic import discontinuous_cycle_mean
    t=np.array([0.,.5,1.,1.,1.5,2.]);y=np.array([1.,1.,1.,0.,0.,0.])
    query=np.array([1.,1.25,1.5,1.75,2.])
    assert np.allclose(discontinuous_cycle_mean(t,y,1.,query),[1.,.75,.5,.25,0.])
