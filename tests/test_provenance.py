import json
from pathlib import Path
import pytest
from rms_emt.config import write_json,sha256
from rms_emt.reporting import verify_run_inputs,load_rms_comparison
from rms_emt.config import load_config
import numpy as np


def test_modified_raw_output_is_rejected(tmp_path):
    (tmp_path/'psse').mkdir();(tmp_path/'pscad'/'raw').mkdir(parents=True)
    write_json(tmp_path/'config.json',{'schema_version':1})
    (tmp_path/'psse'/'solved.sav').write_bytes(b'TEST ONLY')
    write_json(tmp_path/'psse'/'operating_point.json',{'provenance':{'solved_sav_sha256':sha256(tmp_path/'psse'/'solved.sav')}})
    raw=tmp_path/'pscad'/'raw'/'test.out';raw.write_text('TEST ONLY')
    (tmp_path/'pscad'/'StatcomEMT.pscx').write_text('TEST ONLY')
    write_json(tmp_path/'pscad'/'provenance.json',{
        'engine':'PSCAD/EMTDC','operating_point_sha256':sha256(tmp_path/'psse'/'operating_point.json'),
        'project_sha256':sha256(tmp_path/'pscad'/'StatcomEMT.pscx'),'raw_files':{'test.out':sha256(raw)}})
    write_json(tmp_path/'manifest.json',{'stages':{'psse':'completed','pscad':'completed'},
        'config_sha256':sha256(tmp_path/'config.json'),
        'file_hashes':{name:sha256(tmp_path/name) for name in ['psse/operating_point.json','pscad/provenance.json']}})
    verify_run_inputs(tmp_path)
    raw.write_text('MODIFIED TEST ONLY')
    with pytest.raises(ValueError,match='hash'): verify_run_inputs(tmp_path)


def test_prefault_only_rms_cannot_claim_fault_comparison(tmp_path):
    c=load_config('config/demo.json');c['_operating_point_sha256']='TEST ONLY'
    path=tmp_path/'rms.csv';t=np.arange(0,.951,.01)
    np.savetxt(path,np.column_stack([t,np.ones(len(t)),np.ones(len(t)),np.ones(len(t))]),
               delimiter=',',header='time_s,v_pu,i_ka,q_mvar',comments='')
    meta={'source_engine':'PSS/E','equivalent_to_emt':True,
          'quantity_location':'STATCOM injection at PCC','q_sign':'positive injection',
          'frequency_hz':60.,'voltage_kv_ll':230.,'fault':c['fault'],
          'csv_sha256':sha256(path),'operating_point_sha256':'TEST ONLY',
          'model_equivalence_notes':'TEST FIXTURE ONLY'}
    m=tmp_path/'metadata.json';write_json(m,meta)
    c['comparison'].update(rms_csv=str(path),rms_metadata=str(m))
    with pytest.raises(ValueError,match='fault interior coverage'):
        load_rms_comparison(c,{'frequency_hz':60.,'voltage_kv_ll':230.})


@pytest.mark.parametrize('mutation',['modified_outx','unregistered_csv'])
def test_native_rms_output_cannot_be_replaced_after_validation(tmp_path,mutation):
    """Minimal fake files exercise provenance only; they are not simulation results."""
    for name in ['psse','pscad/raw','rms']:(tmp_path/name).mkdir(parents=True)
    for name in ['psse/solved.sav','pscad/StatcomEMT.pscx','pscad/raw/emt.out']:
        (tmp_path/name).write_text('TEST FIXTURE ONLY')
    write_json(tmp_path/'config.json',{'rms':{'enabled':True}})
    write_json(tmp_path/'psse/operating_point.json',{'provenance':{'solved_sav_sha256':sha256(tmp_path/'psse/solved.sav')}})
    op_hash=sha256(tmp_path/'psse/operating_point.json')
    write_json(tmp_path/'pscad/provenance.json',{'engine':'PSCAD/EMTDC','operating_point_sha256':op_hash,
        'project_sha256':sha256(tmp_path/'pscad/StatcomEMT.pscx'),'raw_files':{'emt.out':sha256(tmp_path/'pscad/raw/emt.out')}})
    artifacts={}
    for name in ['dynamics.outx','statcom.dyr','dynamic_powerflow.sav','channels.csv','checks.json','events.json']:
        (tmp_path/'rms'/name).write_text('TEST FIXTURE ONLY');artifacts[name]=sha256(tmp_path/'rms'/name)
    write_json(tmp_path/'rms/metadata.json',{'source_engine':'PSS/E','physical_checks_passed':True,
        'operating_point_sha256':op_hash,'artifacts':artifacts})
    write_json(tmp_path/'manifest.json',{'stages':{'psse':'completed','pscad':'completed','rms':'completed'},
        'config_sha256':sha256(tmp_path/'config.json'),'file_hashes':{name:sha256(tmp_path/name) for name in
        ['psse/operating_point.json','pscad/provenance.json','rms/metadata.json']}})
    verify_run_inputs(tmp_path)
    if mutation=='modified_outx':
        (tmp_path/'rms/dynamics.outx').write_text('MODIFIED TEST FIXTURE')
    else:
        (tmp_path/'rms/native_channels.csv').write_text('UNREGISTERED TEST FIXTURE')
    with pytest.raises(ValueError,match='hash|inventory'): verify_run_inputs(tmp_path)
