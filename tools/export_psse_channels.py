"""Export explicitly mapped, real PSS/E channels to the comparison CSV format.

Usage: py -3.11 tools/export_psse_channels.py filled_mapping.json actual_rms.csv
This exports native results; it never runs or invents a dynamic simulation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mapping');p.add_argument('csv')
    a=p.parse_args();cfg=json.loads(Path(a.mapping).read_text(encoding='utf8'))
    if not cfg.get('output_file') or not Path(cfg['output_file']).is_file():
        raise ValueError('Set output_file to an existing real PSS/E OUT/OUTX file.')
    if Path(a.csv).exists(): raise FileExistsError('Choose a new output CSV path.')
    sys.path.insert(0,cfg['psse_python_path'])
    import psse3506
    import dyntools
    title,ids,data=dyntools.CHNF(cfg['output_file'],outvrsn=cfg['outvrsn']).get_data()
    columns={'time_s':np.asarray(data['time'])}
    for name in ['v_pu','i_ka','q_mvar']:
        spec=cfg['channels'][name];channel=spec['number']
        if not isinstance(channel,int) or channel not in data:
            raise ValueError(f'Set a valid explicit channel number for {name}; available: {ids}')
        columns[name]=np.asarray(data[channel])*float(spec['scale'])
        print(f'{name}: channel {channel}, {ids[channel]}, multiplier {spec["scale"]}')
    array=np.column_stack(list(columns.values()))
    if not np.isfinite(array).all() or np.any(np.diff(array[:,0])<=0):
        raise ValueError('Non-finite data or a non-increasing time axis cannot be compared.')
    np.savetxt(a.csv,array,delimiter=',',header=','.join(columns),comments='',fmt='%.10g')
    print('Native channel export:',a.csv)
    print('CSV SHA-256:',hashlib.sha256(Path(a.csv).read_bytes()).hexdigest())
    print('Complete rms_metadata.json before enabling comparisons; equivalence is not automatic.')


if __name__=='__main__': main()
