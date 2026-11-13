"""Repeat only EMT with half the step, reusing a verified sequential handover.

Usage: py -3.11 tools/check_timestep.py runs/validated_demo runs/timestep_check
This checks numerical step sensitivity, not model or hardware validity.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from rms_emt.cli import worker
from rms_emt.config import load_config,write_json,sha256
from rms_emt.reporting import verify_run_inputs
from rms_emt.results import read_pscad_out,process_waveforms


def measurements(raw,op):
    inf=list(Path(raw).glob('*.inf'))
    if len(inf)!=1: raise ValueError('Exactly one INF is required.')
    t,ch=read_pscad_out(inf[0],basename='emt')
    v=np.column_stack([ch[f'V{p}_kV'] for p in 'abc'])
    i=np.column_stack([ch[f'Is{p}_kA'] for p in 'abc'])
    return process_waveforms(t,v,i,op['frequency_hz'],op['voltage_kv_ll'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline');p.add_argument('output')
    a=p.parse_args();base=Path(a.baseline).resolve();out=Path(a.output).resolve()
    verify_run_inputs(base);c=load_config(base/'config.json');out.mkdir(parents=True,exist_ok=False)
    old_step=c['simulation']['time_step_us'];c['simulation']['time_step_us']=old_step/2
    write_json(out/'config.json',c);load_config(out/'config.json')
    op_path=base/'psse'/'operating_point.json';op=json.loads(op_path.read_text(encoding='utf8'))
    worker('rms_emt.pscad_worker',[out/'config.json',op_path,out/'pscad'],out/'pscad_worker.log',c['simulation']['timeout_s'])
    x=measurements(base/'pscad'/'raw',op);y=measurements(out/'pscad'/'raw',op)
    # Output steps remain identical; interpolate only within the common interval.
    mask=(x['time_s']>=c['simulation']['prefault_window_s'][0])&(x['time_s']<=y['time_s'][-1])
    limits={'v_pu':(.005,.02),'i_ka':(.002,.01),'q_mvar':(1.,5.)};rows=[]
    for key,(rms_limit,max_limit) in limits.items():
        difference=x[key][mask]-np.interp(x['time_s'][mask],y['time_s'],y[key])
        rms=float(np.sqrt(np.mean(difference**2)));maximum=float(np.max(abs(difference)))
        rows.append(dict(quantity=key,rmse=rms,max_abs=maximum,rmse_limit=rms_limit,
                         max_limit=max_limit,passed=rms<=rms_limit and maximum<=max_limit))
    result={'scope':'EMT time-step sensitivity; not equipment/model validation',
        'baseline_step_us':old_step,'refined_step_us':old_step/2,
        'baseline_manifest_sha256':sha256(base/'manifest.json'),'operating_point_sha256':sha256(op_path),
        'checks':rows,'passed':all(r['passed'] for r in rows)}
    write_json(out/'timestep_comparison.json',result);print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
