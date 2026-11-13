"""Licensed PSS/E worker; called in its own Python 3.11 process."""
import argparse
import cmath
import json
import math
import os
import sys
from pathlib import Path
from .config import load_config, write_json, sha256
from .physics import impedance_from_strength, convert_operating_point


def check(code, context):
    if code != 0:
        raise RuntimeError(f'PSS/E {context}: ierr={code}; inspect psse.log.')


def value(result, context):
    check(result[0], context)
    return result[1]


def run(c, folder):
    api=Path(c['psse']['python_path'])
    if sys.version_info[:2] != (3,11) or not (api/'psse3506.py').is_file():
        raise RuntimeError('Use Python 3.11 and configure the installed 35.6/PSSPY311 folder.')
    sys.path.insert(0,str(api))
    import psse3506  # Official minor-version environment bootstrap.
    import psspy
    import pssarrays
    import redirect
    redirect.psse2py()
    print('Initializing PSS/E license...',flush=True)
    check(psspy.psseinit(10000),'psseinit')
    try:
        for fn in [psspy.progress_output,psspy.prompt_output,psspy.report_output,psspy.alert_output]:
            check(fn(2,str(folder/'psse.log'),[0,0]),fn.__name__)
        version=psspy.psseversion()
        if tuple(version[1:3]) != (35,6):
            raise RuntimeError(f'Unexpected PSS/E version: {version}')
        g,p,ld,st=c['grid'],c['psse'],c['load'],c['statcom']
        if p['case_path']:
            case=Path(p['case_path']).resolve()
            if not case.is_file():
                raise FileNotFoundError(f'Missing input SAV: {case}')
            check(psspy.case(str(case)),'case')
            # External mode is deliberately a one-port equivalent. See template contract.
        else:
            check(psspy.newcase_2([0,0],g['base_mva'],g['frequency_hz'],
                                 'Sequential RMS EMT weak grid','Averaged STATCOM terminal demonstration'),'newcase_2')
            for bus,kind,name in [(p['grid_bus'],3,'GRID'),(p['pcc_bus'],1,'PCC230')]:
                check(psspy.bus_data_4(bus,0,[kind,1,1,1],
                      [g['voltage_kv_ll'],1.,0.,1.1,.9,1.2,.8],name),'bus_data_4')
            check(psspy.plant_data_4(p['grid_bus'],0,[0,0],[g['slack_voltage_pu'],100.]),'plant_data_4')
            # Small but nonzero source impedance is INCLUDED in ASCC extraction.
            xs=1e-5
            check(psspy.machine_data_2(p['grid_bus'],'1',[1,1,0,0,0,0],
                  [ld['p_mw'],0.,9999.,-9999.,9999.,-9999.,g['base_mva'],0.,xs,0.,0.,1.,1.,0.,0.,0.,1.]),'machine_data_2')
            check(psspy.newseq(),'newseq')
            check(psspy.seq_machine_data_3(p['grid_bus'],'1',[1],
                  [0.,xs,0.,xs,0.,xs,xs,xs,0.,0.]),'seq_machine_data_3')
            z=impedance_from_strength(g['base_mva'],g['short_circuit_mva'],g['xr_ratio'])-complex(0,xs)
            if z.imag<=0: raise ValueError('Grid branch reactance must remain positive.')
            check(psspy.branch_data_3(p['grid_bus'],p['pcc_bus'],p['boundary_circuit'],
                  [1,p['grid_bus'],1,0,0,0],[z.real,z.imag,0.,0.,0.,0.,0.,0.,1.,0.,0.,0.],
                  [g['short_circuit_mva']]*12,'EXTERNAL_GRID'),'branch_data_3')
            check(psspy.seq_branch_data_3(p['grid_bus'],p['pcc_bus'],p['boundary_circuit'],
                  [0],[z.real,z.imag,0.,0.,0.,0.,0.,0.]),'seq_branch_data_3')
            for ident,pw,q in [(p['load_id'],ld['p_mw'],ld['q_mvar']),
                                (p['statcom_load_id'],0.,-st['q_initial_mvar'])]:
                check(psspy.load_data_6(p['pcc_bus'],ident,[1,1,1,1,1,0,0],
                      [pw,q,0.,0.,0.,0.,0.,0.],''),'load_data_6')
        check(psspy.solution_parameters_5(realar6=1e-6),'solution_parameters_5 TOLN')
        check(psspy.fnsl([0,0,0,1,1,0,99,0]),'fnsl')
        check(psspy.solved(),'solved (convergence)')
        check(psspy.save(str(folder/'solved.sav')),'save')
        base=psspy.sysmva()
        frequency=value(psspy.base_frequency(),'base_frequency')
        if not math.isclose(frequency,g['frequency_hz'],rel_tol=1e-8):
            raise ValueError('Configured frequency differs from the PSS/E case frequency.')
        kv=value(psspy.busdat(p['pcc_bus'],'BASE'),'busdat BASE')
        vm=value(psspy.busdat(p['pcc_bus'],'PU'),'busdat PU')
        va=value(psspy.busdat(p['pcc_bus'],'ANGLED'),'busdat ANGLED')
        v=cmath.rect(vm,math.radians(va))
        # Reverse branch flow: negate power leaving PCC toward external grid.
        boundary=-value(psspy.brnflo(p['pcc_bus'],p['grid_bus'],p['boundary_circuit']),'brnflo')
        load=value(psspy.loddt2(p['pcc_bus'],p['load_id'],'TOTAL','ACT'),'loddt2 LD')
        stat=value(psspy.loddt2(p['pcc_bus'],p['statcom_load_id'],'TOTAL','ACT'),'loddt2 ST')
        if abs(stat.real)>1e-6:
            raise ValueError('This lossless STATCOM model requires zero active power at initialization.')
        if not math.isclose(kv,g['voltage_kv_ll'],rel_tol=1e-6):
            raise ValueError('Configured nominal voltage differs from SAV PCC base.')
        check(psspy.bsys(0,0,[0.,0.],0,[],1,[p['pcc_bus']],0,[],0,[]),'bsys')
        for fn,val in [(psspy.short_circuit_units,0),(psspy.short_circuit_coordinates,0),
                       (psspy.short_circuit_z_units,0),(psspy.short_circuit_z_coordinates,0)]:
            check(fn(val),fn.__name__)
        sc=pssarrays.ascc_currents(0,0,flt3ph=1,voltop=1,volts=1.,genxop=0,
                                  dcload=0,lnchrg=2,shntop=2,loadop=2,machpq=1,rptop=1)
        check(sc.ierr,'ascc_currents')
        if sc.scfmt_z!='rectangular' or sc.scfmt!='rectangular' or sc.scunit!='pu':
            raise ValueError('ASCC must return per-unit current and rectangular coordinates.')
        idx=list(sc.fltbus).index(p['pcc_bus'])
        z=complex(sc.thevzpu[idx].z1)
        op=dict(base_mva=base,voltage_kv_ll=kv,frequency_hz=frequency,
                voltage_pu_real=v.real,voltage_pu_imag=v.imag,z1_pu_real=z.real,z1_pu_imag=z.imag,
                boundary_p_mw=boundary.real,boundary_q_mvar=boundary.imag,
                load_p_mw=load.real,load_q_mvar=load.imag,statcom_q_mvar=-stat.imag)
        write_json(folder/'extracted_values.json',op)
        transfer=convert_operating_point(op,st['rating_mvar'],c['load']['capacitance_nf'])
        transfer['ascc_current_pu']=abs(sc.flt3ph[idx].ia1)
        transfer['ascc_current_ka']=transfer['ascc_current_pu']*base/(math.sqrt(3)*kv)
        expected=base/(math.sqrt(3)*kv*abs(z))
        if not math.isclose(transfer['ascc_current_ka'],expected,rel_tol=1e-4):
            raise ValueError('ASCC current fails the three-phase base/impedance cross-check.')
        transfer['provenance']={'engine':'PSS/E','version':list(version),
            'solved_sav_sha256':sha256(folder/'solved.sav'),
            'ascc_options':'1 pu prefault, rectangular, loads/shunts/charging/FACTS excluded',
            'scope':'balanced one-port external grid; local load retained separately',
            'integration':'sequential offline one-way handover'}
        write_json(folder/'operating_point.json',transfer)
        print('Solved PSS/E power flow and extracted external-grid Z1.',flush=True)
    finally:
        psspy.pssehalt_2()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('config');parser.add_argument('folder')
    args=parser.parse_args();folder=Path(args.folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    run(load_config(args.config),folder)
