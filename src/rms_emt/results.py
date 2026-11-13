"""Native PSCAD ASCII output and explicitly defined electrical measurements."""
import re
from pathlib import Path
import numpy as np


def read_pscad_out(inf_path, basename=None):
    inf_path=Path(inf_path)
    channels={}
    for line in inf_path.read_text(encoding='utf-8-sig',errors='strict').splitlines():
        match=re.search(r'PGB\(\s*(\d+)\s*\).*?Desc\s*=\s*"([^"]+)"',line,re.I)
        if match:
            number,name=int(match[1]),match[2]
            if number in channels or name in channels.values():
                raise ValueError('Duplicate channel index or description in INF file.')
            channels[number]=name
    if not channels: raise ValueError(f'No PGB channel definitions found: {inf_path}')
    prefix=basename or inf_path.stem
    result={};time=None;parts={}
    for number,name in sorted(channels.items()):
        part=(number-1)//10+1;column=(number-1)%10+1
        if part not in parts:
            path=inf_path.parent/f'{prefix}_{part:02d}.out'
            if not path.is_file(): raise ValueError(f'Missing native PSCAD output part: {path}')
            # Native ASCII output can use a Fortran D exponent.
            from io import StringIO
            raw=path.read_text(encoding='ascii')
            lines=raw.splitlines()
            # EMTDC ASCII files may start with a single project-description line.
            if lines and lines[0].strip():
                try:
                    float(lines[0].split()[0].replace('D','E').replace('d','e'))
                except ValueError:
                    lines=lines[1:]
            raw='\n'.join(lines).replace('D','E').replace('d','e')
            a=np.loadtxt(StringIO(raw),ndmin=2)
            if a.shape[0]<2 or a.shape[1]<2 or not np.isfinite(a).all():
                raise ValueError(f'Empty, incomplete or non-finite output: {path}')
            if time is None: time=a[:,0]
            elif len(time)!=len(a) or not np.allclose(time,a[:,0],rtol=0,atol=1e-9):
                raise ValueError('PSCAD output parts have different time axes.')
            parts[part]=a
        if column>=parts[part].shape[1]: raise ValueError(f'Missing column for {name}.')
        result[name]=parts[part][:,column]
    if np.any(np.diff(time)<=0): raise ValueError('Output time must increase strictly.')
    return time,result


def cycle_mean(t,values,frequency_hz):
    """Trailing one-cycle integral, with partial sample interpolation at the boundary."""
    values=np.asarray(values,dtype=float)
    period=1/frequency_hz
    area=np.r_[0,np.cumsum(np.diff(t)*(values[1:]+values[:-1])/2)]
    left=t-period
    # Exact integral of the piecewise-linear waveform inside the boundary sample.
    idx=np.clip(np.searchsorted(t,left,side='right')-1,0,len(t)-2)
    h=left-t[idx]
    slope=(values[idx+1]-values[idx])/(t[idx+1]-t[idx])
    area_left=area[idx]+h*values[idx]+h*h*slope/2
    out=(area-area_left)/period
    out[left<t[0]-1e-12]=np.nan
    return out


def process_waveforms(t,v_abc_kv,i_abc_ka,frequency_hz,base_kv_ll):
    t=np.asarray(t,dtype=float);v=np.asarray(v_abc_kv);i=np.asarray(i_abc_ka)
    if len(t)<3 or v.shape!=(len(t),3) or i.shape!=v.shape:
        raise ValueError('Require time and N x 3 instantaneous voltage/current arrays.')
    if not np.isfinite(t).all() or not np.isfinite(v).all() or not np.isfinite(i).all():
        raise ValueError('Waveforms must be finite.')
    if frequency_hz<=0 or base_kv_ll<=0 or np.any(np.diff(t)<=0):
        raise ValueError('Positive frequency/base and strictly increasing time are required.')
    if np.max(np.diff(t))*frequency_hz>.02:
        raise ValueError('At least 50 samples per fundamental cycle are required.')
    alpha_v=(2*v[:,0]-v[:,1]-v[:,2])/3;beta_v=(v[:,1]-v[:,2])/np.sqrt(3)
    alpha_i=(2*i[:,0]-i[:,1]-i[:,2])/3;beta_i=(i[:,1]-i[:,2])/np.sqrt(3)
    q=1.5*(beta_v*alpha_i-alpha_v*beta_i)
    return {'time_s':t,
        'v_pu':np.sqrt(np.maximum(0,cycle_mean(t,np.mean(v*v,axis=1),frequency_hz)))*np.sqrt(3)/base_kv_ll,
        'i_ka':np.sqrt(np.maximum(0,cycle_mean(t,np.mean(i*i,axis=1),frequency_hz))),
        'p_mw':cycle_mean(t,np.sum(v*i,axis=1),frequency_hz),
        'q_mvar':cycle_mean(t,q,frequency_hz)}


def save_csv(path,columns):
    names=list(columns)
    np.savetxt(path,np.column_stack([columns[n] for n in names]),delimiter=',',
               header=','.join(names),comments='',fmt='%.10g')


def validate_emt(t,ch,c,op,processed):
    """Fail the run if output, schedule, current or initialization is inconsistent."""
    checks=[]
    def record(name,passed,actual,limit):
        checks.append(dict(check=name,passed=bool(passed),actual=float(actual),limit=float(limit)))
    dt=c['simulation']['sample_step_us']*1e-6
    record('Output reaches requested stop time',abs(t[-1]-c['simulation']['duration_s'])<=2*dt,t[-1],c['simulation']['duration_s'])
    record('Uniform output sample interval',np.max(abs(np.diff(t)-dt))<dt*.02,np.max(abs(np.diff(t)-dt)),dt*.02)
    gate=ch['FaultOn']>.5
    changes=np.flatnonzero(np.diff(gate.astype(int)))+1
    if len(changes)!=2 or gate[0] or gate[-1]:
        raise ValueError('Fault output must contain exactly one closed interval.')
    start,end=t[changes]
    record('Fault inception',abs(start-c['fault']['start_s'])<=2*dt,start,c['fault']['start_s'])
    record('Fault duration',abs(end-start-c['fault']['duration_s'])<=2*dt,end-start,c['fault']['duration_s'])
    fault_current=np.column_stack([ch[f'If{p}_kA'] for p in 'abc'])
    voltage=np.column_stack([ch[f'V{p}_kV'] for p in 'abc'])
    inside=(t>start+2*dt)&(t<end-2*dt)
    outside=(t>c['simulation']['prefault_window_s'][0])&((t<start-2*dt)|(t>end+2*dt))
    vf=voltage[inside];fi=fault_current[inside]
    residual=np.linalg.norm(vf-c['fault']['resistance_ohm']*fi)/max(np.linalg.norm(vf),1e-12)
    record('Measured fault branch V=R I',residual<.01,residual,.01)
    leakage=np.max(abs(fault_current[outside]))
    record('Measured fault branches open outside event',leakage<1e-5,leakage,1e-5)
    if c['fault']['resistance_ohm']<.1*np.hypot(op['r_ohm'],op['x_ohm']):
        sag=np.sqrt(np.mean(vf**2))*np.sqrt(3)/op['voltage_kv_ll']
        record('Low-impedance PCC fault causes voltage depression',sag<.3,sag,.3)
    record('STATCOM commanded current limit',np.max(abs(ch['Iq_pu']))<=1.00001,np.max(abs(ch['Iq_pu'])),1.)
    currents=np.column_stack([ch[f'Is{p}_kA'] for p in 'abc'])
    envelope=np.sqrt(2/3*np.sum(currents**2,axis=1))
    record('STATCOM instantaneous current envelope',np.max(envelope)<=np.sqrt(2)*op['rated_current_ka']*1.0001,
           np.max(envelope),np.sqrt(2)*op['rated_current_ka'])
    lo,hi=c['simulation']['prefault_window_s'];mask=(t>=lo)&(t<=hi)
    vm=float(np.mean(processed['v_pu'][mask]));q=float(np.mean(processed['q_mvar'][mask]))
    record('Settled pre-fault voltage agreement',abs(vm-op['pcc_voltage_pu'])<=c['comparison']['prefault_voltage_tolerance_pu'],
           abs(vm-op['pcc_voltage_pu']),c['comparison']['prefault_voltage_tolerance_pu'])
    record('Settled pre-fault reactive power agreement',abs(q-op['statcom_q_mvar'])<=c['comparison']['prefault_q_tolerance_mvar'],
           abs(q-op['statcom_q_mvar']),c['comparison']['prefault_q_tolerance_mvar'])
    spread=np.ptp(processed['v_pu'][mask])
    record('Pre-fault voltage settled',spread<.005,spread,.005)
    p=float(np.mean(processed['p_mw'][mask]))
    record('Pre-fault reactive-only terminal active power',abs(p)<.5,abs(p),.5)
    if all(f'Ig{ph}_kA' in ch for ph in 'abc'):
        igrid=np.column_stack([ch[f'Ig{ph}_kA'] for ph in 'abc'])
        grid=process_waveforms(t,voltage,igrid,op['frequency_hz'],op['voltage_kv_ll'])
        for key,loadkey,label in [('p_mw','load_p_mw','active'),('q_mvar','load_q_mvar','reactive')]:
            expected=op[loadkey]*(vm/op['pcc_voltage_pu'])**2
            supplied=float(np.mean(grid[key][mask]+processed[key][mask]))
            mismatch=abs(supplied-expected)
            record(f'Pre-fault PCC {label} power balance',mismatch<.5,mismatch,.5)
    return checks
