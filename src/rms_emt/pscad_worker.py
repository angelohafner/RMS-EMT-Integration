"""Launch, build and run a dedicated PSCAD 5.1.0 instance."""
import argparse
import json
import shutil
import time
import tempfile
from pathlib import Path
from .config import load_config, write_json, sha256
from .pscad_model import build_model


def run(c, op_path, folder):
    import mhi.pscad
    op=json.loads(Path(op_path).read_text(encoding='utf-8'))
    if op.get('schema_version')!=1 or op.get('provenance',{}).get('engine')!='PSS/E':
        raise ValueError('A validated operating_point.json from PSS/E is required.')
    print('Launching dedicated PSCAD 5.1.0 instance...',flush=True)
    app=mhi.pscad.launch(version=c['pscad']['version'],x64=True,minimize=True,
                         silence=True,timeout=60,load_user_profile=True)
    if app is None: raise RuntimeError('PSCAD launch returned None. Check installation and license.')
    project=None
    original_compilers={}
    # PSCAD 5.1's native/compiler boundary can corrupt non-ASCII project paths.
    # Stage only this new run in a known temporary directory, then copy artifacts back.
    temporary=tempfile.TemporaryDirectory(prefix='rms_emt_')
    scratch=Path(temporary.name).resolve()
    if not str(scratch).isascii():
        app.quit()
        temporary.cleanup()
        raise RuntimeError('Set Windows TEMP to an ASCII path for PSCAD compiler staging.')
    try:
        if not app.licensed(): raise RuntimeError('PSCAD could not acquire a simulation license.')
        compiler=c['pscad']['compiler']
        if compiler not in app.setting_range('fortran_version'):
            raise RuntimeError(f'Configured compiler unavailable: {compiler}')
        settings=app.settings()
        original_compilers={key:settings[key] for key in ['fortran_version','c_version'] if key in settings}
        app.settings(fortran_version=compiler)
        project=build_model(app,scratch/'StatcomEMT.pscx',c,op)
        shutil.copy2(scratch/'StatcomEMT.pscx',folder/'StatcomEMT.pscx')
        print('Building and running native EMTDC network...',flush=True)
        project.run()
        messages=[dict(x) if hasattr(x,'keys') else str(x) for x in project.messages()]
        write_json(folder/'messages.json',messages)
        (folder/'build_output.txt').write_text(project.output(),encoding='utf-8')
        for message in project.messages():
            status=str(getattr(message,'status','')).lower()
            if status in ['error','fatal']:
                raise RuntimeError(f'PSCAD build/run error: {message}')
        raw=folder/'raw';raw.mkdir()
        temp=Path(project.temp_folder)
        files=list(temp.glob('emt*.out'))+list(temp.glob('emt*.inf'))
        # PSCAD may name the INF by the project even when output_filename changes.
        files+=list(temp.glob('*.inf'))
        unique={p.resolve():p for p in files}
        if not any(p.suffix.lower()=='.inf' for p in unique):
            raise RuntimeError(f'No native ASCII INF output found in {temp}. Inspect build_output.txt.')
        for src in unique.values(): shutil.copy2(src,raw/src.name)
        write_json(folder/'provenance.json',{'engine':'PSCAD/EMTDC','version':c['pscad']['version'],
            'automation_library':str(mhi.pscad.VERSION),'compiler':compiler,
            'operating_point_sha256':sha256(op_path),'project_sha256':sha256(folder/'StatcomEMT.pscx'),
            'model':f"averaged reactive current injection, {c['statcom']['rating_mvar']:g} MVAr nominal; no PWM/DC-link/vendor control",
            'raw_files':{p.name:sha256(p) for p in raw.iterdir() if p.is_file()}})
        print('PSCAD run returned native output files.',flush=True)
    finally:
        if project:
            (folder/'last_output.txt').write_text(project.output(),encoding='utf-8')
            write_json(folder/'last_messages.json',[str(m) for m in project.messages()])
        try:
            if original_compilers: app.settings(**original_compilers)
        finally:
            app.quit()
        # Preserve generated source files for engineering review, but not executables.
        if project:
            debug=folder/'generated_source';debug.mkdir(exist_ok=True)
            for suffix in ['*.f','*.f90','*.map','*.dta']:
                for src in scratch.rglob(suffix): shutil.copy2(src,debug/src.name)
        temporary.cleanup()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('operating_point');p.add_argument('folder')
    a=p.parse_args();folder=Path(a.folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    run(load_config(a.config),a.operating_point,folder)
