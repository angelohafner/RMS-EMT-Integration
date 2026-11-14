"""Prepare display assets from verified simulation output; no synthetic result curves."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rms_emt.reporting import verify_run_inputs


def extrema_reduce(t,y,bins=350):
    t=np.asarray(t);y=np.asarray(y)
    if len(t)!=len(y) or not np.isfinite(t).all() or not np.isfinite(y).all():raise ValueError('Invalid display data.')
    if np.any(np.diff(t)<0):raise ValueError('Display time decreases.')
    chosen={0,len(t)-1}
    for group in np.array_split(np.arange(len(t)),min(bins,len(t))):
        chosen.add(int(group[np.argmin(y[group])]))
        chosen.add(int(group[np.argmax(y[group])]))
    idx=np.array(sorted(chosen))
    return t[idx],y[idx]


def main():
    here=ROOT/'video';assets=here/'assets';assets.mkdir(exist_ok=True)
    data={};provenance={'source':'Actual licensed PSS/E and PSCAD output','curves':{},'op':{},'metrics':{}}
    for case,name in [('capacitive','dynamic_capacitive_v2'),('inductive','dynamic_inductive_v2')]:
        run=ROOT/'runs'/name;verify_run_inputs(run)
        provenance['op'][case]=json.loads((run/'psse/operating_point.json').read_text())
        provenance['metrics'][case]=json.loads((run/'report/metrics.json').read_text())
        for engine,filename in [('emt','report/emt_processed.csv'),('rms','report/rms_cycle_envelopes.csv')]:
            path=run/filename;a=np.genfromtxt(path,delimiter=',',names=True)
            mask=(a['time_s']>=.8)&(a['time_s']<=1.4)
            for key in ['v_pu','i_ka','q_mvar']:
                # Keep every recorded row: no display decimation or invented samples.
                t,y=a['time_s'][mask],a[key][mask]
                ident=f'{case}_{engine}_{key}';data[ident+'_t']=t;data[ident]=y
                provenance['curves'][ident]={'source_file':str(path.relative_to(ROOT)).replace('\\','/'),
                    'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'samples':len(t),
                    'source_interval_samples':int(mask.sum()),'selection':'all original rows in [0.8, 1.4] s',
                    'median_output_step_s':float(np.median(np.diff(t))),
                    'full_interval_min':float(a[key][mask].min()),'full_interval_max':float(a[key][mask].max()),
                    'reduced_min':float(y.min()),'reduced_max':float(y.max())}
                if y.max()!=a[key][mask].max() or y.min()!=a[key][mask].min():raise ValueError('Reducer lost an extremum.')
    np.savez_compressed(assets/'measurements.npz',**data)
    provenance['dataset_sha256']=hashlib.sha256((assets/'measurements.npz').read_bytes()).hexdigest()
    (assets/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf8')
    if __package__:
        from .circuit import generate_circuits
    else:
        from circuit import generate_circuits
    generate_circuits(assets)
    print('Verified display data and Schemdraw circuit prepared.')


if __name__=='__main__':main()
