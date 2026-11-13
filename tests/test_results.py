import numpy as np
import pytest
from rms_emt.results import process_waveforms, read_pscad_out
from rms_emt.results import validate_emt
from rms_emt.config import load_config


def test_balanced_reactive_injection_and_rms():
    # Analytical signals are test fixtures only; never delivered as simulator output.
    t=np.arange(0,.2,1e-4)
    a=2*np.pi*50*t[:,None]+np.array([0,-2*np.pi/3,2*np.pi/3])
    v=230/np.sqrt(3)*np.sqrt(2)*np.cos(a)
    i=100/(np.sqrt(3)*230)*np.sqrt(2)*np.sin(a)
    data=process_waveforms(t,v,i,50.,230.)
    assert np.nanmean(data['v_pu']) == pytest.approx(1.,abs=1e-10)
    assert np.nanmean(data['q_mvar']) == pytest.approx(100.,abs=1e-10)
    assert np.nanmean(data['p_mw']) == pytest.approx(0.,abs=1e-10)
    assert np.isnan(data['v_pu'][0])


def test_nonmonotonic_time_rejected():
    with pytest.raises(ValueError):
        process_waveforms(np.array([0.,.1,.1]),np.ones((3,3)),np.ones((3,3)),60.,230.)


def test_inf_mapping_and_missing_part_rejected(tmp_path):
    (tmp_path/'x.inf').write_text('PGB(1) Output Desc="Va_kV" Group="" Max=1 Min=0 Units="kV"\n')
    (tmp_path/'x_01.out').write_text('0 1\n0.001 2\n')
    t,channels=read_pscad_out(tmp_path/'x.inf')
    assert channels['Va_kV'].tolist()==[1,2]
    (tmp_path/'x_01.out').unlink()
    with pytest.raises(ValueError): read_pscad_out(tmp_path/'x.inf')


def test_native_title_line_and_fortran_exponents(tmp_path):
    (tmp_path/'x.inf').write_text('PGB(1) Output Desc="Va_kV"\n')
    (tmp_path/'x_01.out').write_text('Native PSCAD project description\n0.0 1.2D+01\n1.0D-04 2.0D+01\n')
    t,ch=read_pscad_out(tmp_path/'x.inf')
    assert ch['Va_kV'].tolist()==[12.,20.]


def test_nonfinite_first_data_row_is_not_mistaken_for_title(tmp_path):
    (tmp_path/'x.inf').write_text('PGB(1) Output Desc="Va_kV"\n')
    (tmp_path/'x_01.out').write_text('nan 1\n0.001 2\n0.002 3\n')
    with pytest.raises(ValueError,match='non-finite'): read_pscad_out(tmp_path/'x.inf')


def test_fault_command_without_electrical_fault_cannot_pass():
    c=load_config('config/demo.json');t=np.arange(0,2.00001,1e-4)
    c['simulation']['sample_step_us']=100.
    a=2*np.pi*60*t[:,None]+np.array([0,-2*np.pi/3,2*np.pi/3])
    v=230*np.sqrt(2/3)*np.cos(a);i=20/(np.sqrt(3)*230)*np.sqrt(2)*np.sin(a)
    ch={'FaultOn':((t>=1)&(t<1.15)).astype(float),'Iq_pu':np.full(len(t),.2)}
    for k,p in enumerate('abc'):
        ch[f'V{p}_kV']=v[:,k];ch[f'Is{p}_kA']=i[:,k];ch[f'If{p}_kA']=np.zeros(len(t))
    op={'voltage_kv_ll':230.,'rated_current_ka':100/(np.sqrt(3)*230),'pcc_voltage_pu':1.,
        'statcom_q_mvar':20.,'r_ohm':17.5,'x_ohm':175.}
    checks=validate_emt(t,ch,c,op,process_waveforms(t,v,i,60.,230.))
    assert not next(x['passed'] for x in checks if x['check']=='Measured fault branch V=R I')
    assert not all(x['passed'] for x in checks)
