"""Repeat native RMS at half step and assess cycle envelopes, including events."""
import argparse
import json
from pathlib import Path
import numpy as np
from rms_emt.cli import compare_existing
from rms_emt.config import load_config,sha256,write_json
from rms_emt.reporting import verify_run_inputs
from rms_emt.dynamic import rms_cycle_envelopes


def main():
    p=argparse.ArgumentParser();p.add_argument('baseline');p.add_argument('output');a=p.parse_args()
    source=Path(a.baseline).resolve();target=Path(a.output).resolve();verify_run_inputs(source)
    c=load_config(source/'config.json')
    if not c.get('rms',{}).get('enabled'): raise ValueError('Baseline must include native RMS dynamics.')
    if not (source/'rms'/'native_channels.csv').is_file():
        raise ValueError('Baseline must preserve native pre/post-event samples; rerun it with the current adapter first.')
    old=c['rms']['time_step_s'];new=old/2
    # Declare limits before running. Native phasor voltage is discontinuous at events,
    # so use the same one-cycle envelopes used in the RMS/EMT report for this check.
    limits={'v_pu':(.005,.03),'i_ka':(.001,.005),'q_mvar':(.5,3.)}
    compare_existing(source,target,new)
    verify_run_inputs(target)
    b=np.genfromtxt(source/'rms'/'channels.csv',delimiter=',',names=True)
    r=np.genfromtxt(target/'rms'/'channels.csv',delimiter=',',names=True)
    bn=np.genfromtxt(source/'rms'/'native_channels.csv',delimiter=',',names=True)
    rn=np.genfromtxt(target/'rms'/'native_channels.csv',delimiter=',',names=True)
    start=c['simulation']['prefault_window_s'][0];end=min(c['simulation']['duration_s'],b['time_s'][-1],r['time_s'][-1])
    t=r['time_s'];mask=(t>=start)&(t<=end);frequency=c['grid']['frequency_hz']
    rows=[]
    be=rms_cycle_envelopes(bn,t,frequency);re=rms_cycle_envelopes(rn,t,frequency)
    for key,(rms_limit,max_limit) in limits.items():
        delta=re[key][mask]-be[key][mask]
        rmse=float(np.sqrt(np.mean(delta**2)));maximum=float(np.max(abs(delta)))
        rows.append(dict(quantity=key,rmse=rmse,max_abs=maximum,rmse_limit=rms_limit,max_abs_limit=max_limit,
                         passed=rmse<=rms_limit and maximum<=max_limit))
    result=dict(passed=all(x['passed'] for x in rows),baseline_step_s=old,refined_step_s=new,
        window_s=[start,end],measurement='one-cycle phasor envelopes; no event windows excluded',
        baseline_metadata_sha256=sha256(source/'rms'/'metadata.json'),
        refined_metadata_sha256=sha256(target/'rms'/'metadata.json'),rows=rows)
    write_json(target/'rms_timestep_comparison.json',result)
    print(json.dumps(result,indent=2))
    if not result['passed']: raise RuntimeError('RMS time-step criteria failed.')


if __name__=='__main__': main()
