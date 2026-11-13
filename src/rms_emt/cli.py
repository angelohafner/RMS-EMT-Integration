"""Command-line orchestration with isolated workers and auditable run directories."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import shutil
from .config import load_config, write_json, sha256


def worker(module,args,log_path,timeout):
    env=os.environ.copy()
    env['PYTHONPATH']=str(Path(__file__).resolve().parents[1])+os.pathsep+env.get('PYTHONPATH','')
    env['PYTHONUNBUFFERED']='1'
    with Path(log_path).open('w',encoding='utf8') as stream:
        process=subprocess.Popen([sys.executable,'-u','-m',module,*map(str,args)],
            stdout=stream,stderr=subprocess.STDOUT,env=env)
        try:
            code=process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            import psutil
            parent=psutil.Process(process.pid)
            children=parent.children(recursive=True)
            for child in children:
                try: child.terminate()
                except psutil.NoSuchProcess: pass
            parent.terminate()
            _,alive=psutil.wait_procs([parent,*children],timeout=5)
            for child in alive:
                try: child.kill()
                except psutil.NoSuchProcess: pass
            raise RuntimeError(f'{module} exceeded {timeout} seconds; see {log_path}.') from exc
    if code: raise RuntimeError(f'{module} failed with exit code {code}; see {log_path}.')


def execute(config_path,output):
    c=load_config(config_path)
    run=Path(output).resolve()
    run.mkdir(parents=True,exist_ok=False)
    # Freeze relative input paths against the invoking directory before starting workers.
    for section,key in [('psse','case_path'),('comparison','rms_csv'),('comparison','rms_metadata')]:
        if c[section][key]: c[section][key]=str(Path(c[section][key]).resolve())
    snapshot=run/'config.json';write_json(snapshot,c)
    manifest={'schema_version':1,'started_utc':datetime.now(timezone.utc).isoformat(),
        'status':'running','python':sys.version,'config_sha256':sha256(snapshot),
        'integration':'sequential offline one-way','stages':{},'file_hashes':{}}
    write_json(run/'manifest.json',manifest)
    try:
        for name,module,args in [
            ('psse','rms_emt.psse_worker',[snapshot,run/'psse']),
            ('pscad','rms_emt.pscad_worker',[snapshot,run/'psse'/'operating_point.json',run/'pscad'])]:
            print(f'{name.upper()} stage started. Log: {run/(name+"_worker.log")}',flush=True)
            worker(module,args,run/(name+'_worker.log'),c['simulation']['timeout_s'])
            manifest['stages'][name]='completed'
            relative='psse/operating_point.json' if name=='psse' else 'pscad/provenance.json'
            manifest['file_hashes'][relative]=sha256(run/relative)
            write_json(run/'manifest.json',manifest)
        from .reporting import report
        if c.get('rms',{}).get('enabled'):
            run_rms_stage(run,c,manifest)
        metrics=report(run,c)
        manifest['stages']['report']='completed'
        manifest['status']='passed' if metrics['validation_passed'] else 'failed_validation'
        manifest['metrics']=metrics
        if not metrics['validation_passed']:
            raise RuntimeError('Physical checks failed; inspect report/report.html and checks.json.')
        print(f'Validated run: {run}\nReport: {run/"report"/"report.html"}',flush=True)
    except Exception as exc:
        manifest['status']='failed';manifest['error']=str(exc)
        raise
    finally:
        manifest['finished_utc']=datetime.now(timezone.utc).isoformat()
        write_json(run/'manifest.json',manifest)


def run_rms_stage(run,c,manifest):
    print(f'Native RMS stage started. Log: {run/"rms_worker.log"}',flush=True)
    worker('rms_emt.psse_dynamic_worker',[run/'config.json',run/'psse'/'operating_point.json',run/'rms'],
           run/'rms_worker.log',c['simulation']['timeout_s'])
    manifest['stages']['rms']='completed'
    manifest['file_hashes']['rms/metadata.json']=sha256(run/'rms'/'metadata.json')
    write_json(run/'manifest.json',manifest)


def compare_existing(source,output,time_step):
    from .reporting import verify_run_inputs,report
    from .config import validate_config
    source=Path(source).resolve();verify_run_inputs(source)
    c=load_config(source/'config.json')
    c['rms']={'enabled':True,'time_step_s':time_step}
    c['comparison']['rms_csv']=None;c['comparison']['rms_metadata']=None
    validate_config(c)
    run=Path(output).resolve()
    if run.is_relative_to(source):
        raise ValueError('Comparison output must be outside the source run to avoid recursive copying.')
    run.mkdir(parents=True,exist_ok=False)
    for name in ['psse','pscad']: shutil.copytree(source/name,run/name)
    write_json(run/'config.json',c)
    original=json.loads((source/'manifest.json').read_text(encoding='utf8'))
    manifest=dict(schema_version=1,status='running',started_utc=datetime.now(timezone.utc).isoformat(),
        integration='sequential offline; native RMS versus previously executed native EMT',
        config_sha256=sha256(run/'config.json'),source_run_manifest_sha256=sha256(source/'manifest.json'),
        stages={'psse':'completed','pscad':'completed'},
        file_hashes={k:original['file_hashes'][k] for k in ['psse/operating_point.json','pscad/provenance.json']})
    write_json(run/'source_config.json',load_config(source/'config.json'))
    write_json(run/'manifest.json',manifest)
    try:
        run_rms_stage(run,c,manifest)
        metrics=report(run,c)
        manifest['stages']['report']='completed';manifest['metrics']=metrics
        if not metrics['validation_passed']: raise RuntimeError('Combined RMS/EMT checks failed.')
        manifest['status']='passed'
        print(f'Validated dynamic comparison: {run/"report"/"report.html"}',flush=True)
    except Exception as exc:
        manifest['status']='failed';manifest['error']=str(exc);raise
    finally:
        manifest['finished_utc']=datetime.now(timezone.utc).isoformat()
        write_json(run/'manifest.json',manifest)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['run','validate','doctor']:
        s=sub.add_parser(name);s.add_argument('--config',default='config/demo.json')
        if name=='run': s.add_argument('--output')
    s=sub.add_parser('report');s.add_argument('run_directory')
    s=sub.add_parser('compare');s.add_argument('source_run');s.add_argument('--output',required=True)
    s.add_argument('--rms-step-s',type=float,default=.0005)
    a=p.parse_args()
    try:
        if a.command=='compare':
            compare_existing(a.source_run,a.output,a.rms_step_s);return 0
        if a.command=='report':
            from .reporting import report
            d=Path(a.run_directory);result=report(d,load_config(d/'config.json'))
            print(json.dumps(result,indent=2));return 0 if result['validation_passed'] else 1
        c=load_config(a.config)
        if a.command=='validate': print('Configuration is valid; no simulators were run.');return 0
        if a.command=='doctor':
            info={'python':sys.version,'python_compatible':sys.version_info[:2]==(3,11),
                'psse_bootstrap_exists':(Path(c['psse']['python_path'])/'psse3506.py').is_file()}
            try:
                import mhi.pscad
                info['pscad_versions']=mhi.pscad.versions();info['automation_library']=str(mhi.pscad.VERSION)
            except ImportError: info['pscad_versions']=[]
            print(json.dumps(info,indent=2));print('Licenses and compiler execution are checked during a real run.')
            return 0 if info['python_compatible'] and info['psse_bootstrap_exists'] and info['pscad_versions'] else 1
        output=a.output or str(Path('runs')/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]))
        execute(a.config,output);return 0
    except (ValueError,RuntimeError,OSError,KeyError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 1


if __name__=='__main__': raise SystemExit(main())
