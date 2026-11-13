"""Package source plus verified native evidence; exclude development probes/runs."""
import argparse
import json
from pathlib import Path
import zipfile
from rms_emt.config import sha256,write_json
from rms_emt.reporting import verify_run_inputs


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='delivery/RMS_EMT_STATCOM_Demo.zip')
    p.add_argument('--dynamic',action='store_true',help='Include the verified native dynamic extension.')
    a=p.parse_args();root=Path(__file__).resolve().parents[1];archive=(root/a.output).resolve()
    if archive.exists(): raise FileExistsError('Choose a new archive path.')
    for name in ['release_capacitive','release_inductive']:
        run=root/'runs'/name;verify_run_inputs(run)
        if json.loads((run/'manifest.json').read_text())['status']!='passed':
            raise ValueError(f'Cannot package {name} as validated.')
    convergence=root/'runs'/'release_timestep'/'timestep_comparison.json'
    if not json.loads(convergence.read_text())['passed']:
        raise ValueError('The final time-step check did not pass.')
    dynamic_runs=['dynamic_capacitive_v2','dynamic_inductive_v2','dynamic_timestep_v2'] if a.dynamic else []
    for name in dynamic_runs:
        run=root/'runs'/name;verify_run_inputs(run)
        if json.loads((run/'manifest.json').read_text())['status']!='passed':
            raise ValueError(f'Cannot package {name} as validated.')
    if a.dynamic and not json.loads((root/'runs'/'dynamic_timestep_v2'/'rms_timestep_comparison.json').read_text())['passed']:
        raise ValueError('RMS time-step check did not pass.')
    files=[]
    for name in ['README.md','pyproject.toml','requirements-tested.txt','.gitignore']:
        files.append(root/name)
    for name in ['src','tests','config','templates','docs']:
        files.extend(p for p in (root/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    for name in ['check_timestep.py','check_rms_timestep.py','export_psse_channels.py','package_delivery.py']:
        files.append(root/'tools'/name)
    # Keep the editable film and its test dependency when packaging the combined project.
    for path in (root/'video').iterdir():
        if path.is_file() and path.suffix in {'.py','.md','.json','.srt','.txt','.ps1'}:
            files.append(path)
    for name in ['assets','audio']:
        files.extend(p for p in (root/'video'/name).rglob('*') if p.is_file())
    files.extend([root/'.gitattributes',root/'CONTEXT.md',
                  root/'delivery'/'RMS_EMT_STATCOM_Dynamic_v2_MANIFEST.json'])
    for name in ['release_capacitive','release_inductive','release_timestep',*dynamic_runs]:
        files.extend(p for p in (root/'runs'/name).rglob('*') if p.is_file())
    paths={str(p.relative_to(root)).replace('\\','/'):sha256(p) for p in sorted(set(files))}
    manifest=archive.with_name(archive.stem+'_MANIFEST.json');write_json(manifest,{'files':paths})
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(paths): z.write(root/path,'RMS_EMT_STATCOM/'+path)
        z.write(manifest,'RMS_EMT_STATCOM/PACKAGE_MANIFEST.json')
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad: raise ValueError(f'ZIP integrity failure: {bad}')
    print(json.dumps({'archive':str(archive),'files':len(paths)+1,'bytes':archive.stat().st_size,'sha256':sha256(archive)},indent=2))


if __name__=='__main__': main()
