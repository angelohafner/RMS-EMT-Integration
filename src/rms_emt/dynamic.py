"""Documented SVSMO3T2 mapping and strict native RMS data utilities."""
import math
import numpy as np


def validate_rms_settings(c):
    r=c.get('rms',{})
    dt=r.get('time_step_s',.0005)
    if not isinstance(dt,(int,float)) or not math.isfinite(dt) or dt<=0 or dt>min(.01,c['statcom']['current_tau_s'])/20:
        raise ValueError('RMS time_step_s must resolve the fastest control lag with at least 20 steps.')
    for event in [c['fault']['start_s'],c['fault']['duration_s'],c['simulation']['duration_s']]:
        if not math.isclose(event/dt,round(event/dt),rel_tol=0,abs_tol=1e-6):
            raise ValueError('RMS step must divide every fault event and the simulation end.')
    if c['psse']['case_path']:
        raise ValueError('Native RMS adapter currently supports the generated two-bus demonstration only.')
    return dt


def model_parameters(c):
    # Order follows ModelLibrary 35.6.4, SVSMO3T2, CON(J)..CON(J+43).
    # Initial native bias is moved into Vref because saturation resets the Ki=0 state.
    # Xc0=0 avoids adding feedback droop to the already proportional 1/droop law.
    return dict(Xc0=0.,Tc1=0.,Tb1=.01,Kp=1/c['statcom']['droop_pu'],KI=0.,
        Vemax=10.,Vemin=-10.,T0=c['statcom']['current_tau_s'],Imax1=1.,
        dbd=0.,Kdbd=0.,Tdbd=0.,Kpr=0.,KIr=0.,Idbd=1.,Vrmax=10.,Vrmin=-10.,
        Ishrt=1.,UV1=.0001,UV2=0.,OV1=5.,OV2=6.,Vtrip=7.,Tdelay1=10.,
        Tdelay2=10.,Vrefmax=10.,Vrefmin=0.,Tc2=0.,Tb2=0.,I2t=100.,Reset=1.,
        hyst=.01,Xc1=0.,Xc2=0.,Xc3=0.,V1=1.1,V2=.9,Tmssbrk=0.,Tout=10.,
        TdelLC=10.,Iupr=1.,Ilwr=-1.,Sdelay=0.,STBASE=c['statcom']['rating_mvar'])


def dyr_text(c):
    icons=[str(c['psse']['pcc_bus']),'0','0','0']+['0',"'1'"]*8
    values=' '.join(format(v,'.12g') for v in model_parameters(c).values())
    return (f"{c['psse']['grid_bus']} 'GENCLS' '1' 0.0 0.0 /\n"
            +"'STATCOM' 'SVSMO3T2' "+' '.join(icons)+'\n'+values+' /\n')


def controller_initialization(c,op):
    iq0=op['statcom_q_mvar']/c['statcom']['rating_mvar']/op['pcc_voltage_pu']
    return dict(integrator_bias_pu=0.,voltage_reference_pu=op['pcc_voltage_pu']+c['statcom']['droop_pu']*iq0)


def normalize_channels(time,voltage,signed_i_pu,q_mvar,rating,kv,**extra):
    a=np.column_stack([time,voltage,signed_i_pu,q_mvar,*extra.values()]).astype(float)
    if len(a)<3 or not np.isfinite(a).all() or np.any(np.diff(a[:,0])<0):
        raise ValueError('Native RMS channels have invalid/nonfinite values or decreasing time.')
    # PSS/E may write before/after event samples at identical times. Preserve raw OUTX;
    # choose the last (post-event) value only for the strictly increasing comparison CSV.
    a=a[np.r_[np.diff(a[:,0])>0,True]]
    return dict(time_s=a[:,0],v_pu=a[:,1],i_ka=abs(a[:,2])*rating/(np.sqrt(3)*kv),
                q_mvar=a[:,3],iq_pu=a[:,2],**{k:a[:,4+i] for i,k in enumerate(extra)})


def current_lag_residual(t,iq,command,tau):
    """Independent piecewise-constant-midpoint reconstruction of the native lag."""
    predicted=np.empty(len(t));predicted[0]=iq[0]
    for k in range(1,len(t)):
        a=np.exp(-(t[k]-t[k-1])/tau)
        predicted[k]=a*predicted[k-1]+(1-a)*(command[k]+command[k-1])/2
    return float(max(abs(predicted-iq)))


def discontinuous_cycle_mean(t,y,frequency,query):
    """Integrate native pre/post-event samples without interpolating across a jump."""
    t=np.asarray(t);y=np.asarray(y);query=np.asarray(query)
    if len(t)<3 or not np.isfinite(t).all() or not np.isfinite(y).all() or np.any(np.diff(t)<0):
        raise ValueError('Nonfinite or decreasing native integration time axis.')
    delta=np.diff(t);area=np.r_[0.,np.cumsum(delta*(y[1:]+y[:-1])/2)]
    slope=np.divide(np.diff(y),delta,out=np.zeros(len(delta)),where=delta>0)
    def primitive(x):
        idx=np.clip(np.searchsorted(t,x,side='right')-1,0,len(t)-2)
        h=x-t[idx]
        return area[idx]+h*y[idx]+.5*h*h*slope[idx]
    left=query-1/frequency
    result=(primitive(query)-primitive(left))*frequency
    result[(left<t[0]-1e-10)|(query>t[-1]+1e-10)]=np.nan
    return result


def rms_cycle_envelopes(native,query,frequency):
    result={'time_s':query}
    for key in ['v_pu','i_ka','q_mvar']:
        if key=='q_mvar': result[key]=discontinuous_cycle_mean(native['time_s'],native[key],frequency,query)
        else: result[key]=np.sqrt(np.maximum(0,discontinuous_cycle_mean(native['time_s'],native[key]**2,frequency,query)))
    return result


def fault_voltage_bound(c,op):
    """Triangle bound for the RMS Norton network with a bounded STATCOM current."""
    z=complex(op['r_ohm'],2*np.pi*op['frequency_hz']*op['l_h'])
    nominal_phase=op['voltage_kv_ll']/np.sqrt(3)
    yload=complex(op['load_p_mw'],-op['load_q_mvar'])/(op['voltage_kv_ll']*op['pcc_voltage_pu'])**2
    yn=1/z+yload+1/c['fault']['resistance_ohm']
    return (op['source_kv_ll']/np.sqrt(3)/abs(z)+op['rated_current_ka'])/abs(yn)/nominal_phase


def validate_rms(data,c,op,events,initialization):
    t=data['time_s'];v=data['v_pu'];iq=data['iq_pu'];q=data['q_mvar']
    dt=validate_rms_settings(c);start=c['fault']['start_s'];end=start+c['fault']['duration_s']
    pre=(t>=c['simulation']['prefault_window_s'][0])&(t<=c['simulation']['prefault_window_s'][1])
    margin=min(.02,c['fault']['duration_s']/5)
    fault=(t>start+margin)&(t<end-margin)
    post=(t>=c['simulation']['duration_s']-.1)
    rating=c['statcom']['rating_mvar'];iq0=op['statcom_q_mvar']/rating/op['pcc_voltage_pu']
    checks=[]
    def add(name,passed,detail): checks.append(dict(name=name,passed=bool(passed),detail=detail))
    add('Native RMS full duration',t[-1]>=c['simulation']['duration_s']-2*dt,f'End {t[-1]:.9g} s')
    add('RMS pre-fault voltage match',abs(np.mean(v[pre])-op['pcc_voltage_pu'])<1e-4,f'{np.mean(v[pre]):.9g} pu')
    add('RMS pre-fault Q match',abs(np.mean(q[pre])-op['statcom_q_mvar'])<.01,f'{np.mean(q[pre]):.9g} MVAr')
    add('RMS pre-fault equilibrium',np.ptp(v[pre])<1e-5 and np.ptp(q[pre])<.01,'No initialization drift')
    add('Native current limit',max(abs(iq))<=1.0001,f'Peak {max(abs(iq)):.9g} pu')
    add('Native Q equals V times reactive current',max(abs(q-v*iq*rating))<.01,
        f'Max residual {max(abs(q-v*iq*rating)):.6g} MVAr')
    bound=fault_voltage_bound(c,op)
    add('Fault voltage respects network/current bound',max(v[fault])<=bound*1.001+1e-6,
        f'Peak interior {max(v[fault]):.9g} pu; bound {bound:.9g} pu')
    lag_error=current_lag_residual(t,iq,data['command_iq_pu'],c['statcom']['current_tau_s'])
    lag_tolerance=max(.001,2*dt/c['statcom']['current_tau_s'])
    add('Configured native current lag',lag_error<lag_tolerance,f'Max residual {lag_error:.6g} pu; limit {lag_tolerance:.6g}')
    add('Actual fault application time',abs(events[0]['actual_time_s']-start)<2*dt,str(events[0]))
    add('Actual fault duration',abs(events[1]['actual_time_s']-events[0]['actual_time_s']-c['fault']['duration_s'])<2*dt,
        f"{events[1]['actual_time_s']-events[0]['actual_time_s']:.9g} s")
    add('Post-fault voltage recovery',abs(np.mean(v[post])-op['pcc_voltage_pu'])<.005,f'{np.mean(v[post]):.9g} pu')
    expected=controller_initialization(c,op)
    add('Initialized proportional-controller reference',abs(initialization['integrator_bias_pu'])<1e-7 and
        abs(initialization['voltage_reference_pu']-expected['voltage_reference_pu'])<1e-6,
        f"Zero integrator; Vref {initialization['voltage_reference_pu']:.9g} pu")
    # Initial STRT output is before the coordinate change; compare after startup.
    settled=t>=c['simulation']['prefault_window_s'][0]
    add('Inactive integral state remains zero',max(abs(data['integrator_state_pu'][settled]))<1e-7,
        f"Peak {max(abs(data['integrator_state_pu'][settled])):.9g} pu")
    target=np.clip((data['vref_pu']-data['vmeas_pu'])/c['statcom']['droop_pu'],-1,1)
    add('Native controller follows matched droop law',max(abs(target[settled]-data['command_iq_pu'][settled]))<1e-5,
        f"Max command residual {max(abs(target[settled]-data['command_iq_pu'][settled])):.6g} pu")
    fault_power=-data['pcc_to_grid_p_mw'][fault]-op['load_p_mw']*(v[fault]/op['pcc_voltage_pu'])**2
    expected_power=(v[fault]*op['voltage_kv_ll'])**2/c['fault']['resistance_ohm']
    residual=max(abs(fault_power-expected_power))
    add('Actual resistive fault power balance',residual<.01,f'Max residual {residual:.6g} MW')
    return checks
