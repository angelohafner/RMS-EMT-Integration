"""Run native PSS/E GENCLS and SVSMO3T2, preserving native OUTX evidence."""
import argparse
import json
import math
from pathlib import Path
import sys
from .config import load_config,write_json,sha256
from .psse_worker import check,value
from .dynamic import validate_rms_settings,model_parameters,dyr_text,normalize_channels,validate_rms,controller_initialization
from .results import save_csv


def run(c,op_path,folder):
    dt=validate_rms_settings(c);op=json.loads(op_path.read_text(encoding='utf8'))
    if sys.version_info[:2]!=(3,11): raise RuntimeError('PSS/E 35.6 adapter requires Python 3.11.')
    sys.path.insert(0,c['psse']['python_path'])
    import psse3506
    import psspy
    import redirect
    redirect.psse2py()
    print('Initializing native PSS/E dynamic simulation...',flush=True)
    check(psspy.psseinit(10000),'psseinit')
    events=[]
    try:
        for fn in [psspy.progress_output,psspy.prompt_output,psspy.report_output,psspy.alert_output]:
            check(fn(2,str(folder/'psse_dynamic.log'),[0,0]),fn.__name__)
        version=psspy.psseversion()
        if tuple(version[1:3])!=(35,6): raise RuntimeError(f'Wrong PSS/E version: {version}')
        sav=op_path.parent/'solved.sav'
        if sha256(sav)!=op['provenance']['solved_sav_sha256']: raise ValueError('Input SAV hash mismatch.')
        check(psspy.case(str(sav)),'case')
        p=c['psse'];bus=p['pcc_bus'];rating=c['statcom']['rating_mvar']
        # Remove the static negative-Q load so dynamic injection is not counted twice.
        check(psspy.load_data_6(bus,p['statcom_load_id'],intgar1=0),'disable static STATCOM load')
        value(psspy.facts_data_3('STATCOM',[bus,0,1,1,0,bus,0],
              [0.,0.,op['pcc_voltage_pu'],rating,0.,.1,2.,1.,0.,.05,100.,0.,0.],''),'facts_data_3')
        check(psspy.solution_parameters_5(realar6=1e-6),'solution tolerance')
        check(psspy.fnsl([0,0,0,1,1,0,99,0]),'FACTS power flow')
        check(psspy.solved(),'FACTS power flow convergence')
        check(psspy.save(str(folder/'dynamic_powerflow.sav')),'save dynamic power flow')
        dyr=folder/'statcom.dyr';dyr.write_text(dyr_text(c),encoding='ascii')
        check(psspy.dyre_new([1,1,1,1],str(dyr),'','',''),'dyre_new')
        check(psspy.cong(0),'cong')
        for mode in [1,2,3]: value(psspy.conl(0,1,mode,[0,0],[0.,100.,0.,100.]),f'conl {mode}')
        check(psspy.ordr(0),'ordr');check(psspy.fact(),'fact');check(psspy.tysl(0),'tysl')
        check(psspy.dynamics_solution_param_2(intgar1=100,realar1=.4,realar2=1e-6,realar3=dt),'dynamics solution')
        indices={k:value(psspy.fcdmind('STATCOM',k),'fcdmind '+k) for k in ['CON','STATE','VAR','NCON','NSTATE','NVAR','STATUS']}
        if indices['NCON']!=44 or indices['STATUS']!=1: raise RuntimeError('Native SVSMO3T2 is not active.')
        base=indices['VAR'];state=indices['STATE']
        check(psspy.voltage_channel([1,-1,-1,bus],'PCC_V_PU'),'voltage_channel')
        for channel,offset,label in [(2,0,'STATCOM_IQ_PU'),(3,2,'STATCOM_Q_MVAR'),(4,8,'VMEAS_PU'),
                                     (5,3,'IQ_COMMAND_PU'),(6,6,'VREF_PU')]:
            check(psspy.var_channel([channel,base+offset],label),'var_channel '+label)
        check(psspy.state_channel([7,state+1],'INTEGRATOR_STATE_PU'),'state_channel')
        check(psspy.branch_p_and_q_channel([8,-1,-1,bus,p['grid_bus']],p['boundary_circuit'],
              ['PCC_TO_GRID_P_MW','PCC_TO_GRID_Q_MVAR']),'branch_p_and_q_channel')
        output=folder/'dynamics.outx'
        check(psspy.strt_2([0,0],str(output)),'strt_2')
        # Exact initial-condition reparameterization: Iq0 + Kp*(Vop-Vm)
        # equals Kp*(Vop+Iq0/Kp-Vm). The native Ki=0 limiter resets its state
        # at saturation, so place the bias in Vref, not in that resettable state.
        # Apply once before RUN; never overwrite states during the simulation.
        desired=controller_initialization(c,op)
        check(psspy.change_state(state+1,[0.,0.,0.]),'zero inactive integrator state/derivative/memory')
        for relative in [7,26]:
            check(psspy.change_fctmod_var('STATCOM','SVSMO3T2',relative,desired['voltage_reference_pu']),
                  'initialize Vref and Vscheduled')
        init={name:value(psspy.dsrval(kind,index),'read '+name) for name,kind,index in [
            ('integrator_bias_pu','STATE',state+1),('iq_pu','VAR',base),('q_mvar','VAR',base+2),
            ('voltage_reference_pu','VAR',base+6)]}
        write_json(folder/'initialization.json',init)
        check(psspy.snap([-1,-1,-1,-1,-1],str(folder/'initialized.snp')),'snap')
        def run_exact(target):
            # PSS/E accumulates TIME in single precision. Avoid one-step event
            # overshoot by taking a final, explicitly sized step to the boundary.
            check(psspy.run(0,target-dt,0,1,0),'run toward exact boundary')
            now=value(psspy.dsrval('TIME',0),'TIME before final event step')
            remaining=target-now
            if not 0<remaining<=1.1*dt:
                raise RuntimeError(f'Cannot align native boundary: time={now}, target={target}, dt={dt}')
            check(psspy.dynamics_solution_param_2(realar3=remaining),'last partial integration step')
            check(psspy.run(0,target,0,1,0),'run to exact boundary')
            actual=value(psspy.dsrval('TIME',0),'TIME at exact boundary')
            check(psspy.dynamics_solution_param_2(realar3=dt),'restore nominal integration step')
            if abs(actual-target)>2e-7:
                raise RuntimeError(f'Native event alignment failed: {actual} versus {target}')
        run_exact(c['fault']['start_s'])
        events.append(dict(event='apply',requested_time_s=c['fault']['start_s'],actual_time_s=value(psspy.dsrval('TIME',0),'TIME')))
        check(psspy.dist_3phase_bus_fault(bus,0,3,op['voltage_kv_ll'],[c['fault']['resistance_ohm'],0.]),'dist_3phase_bus_fault ohms')
        end=c['fault']['start_s']+c['fault']['duration_s']
        run_exact(end)
        events.append(dict(event='clear',requested_time_s=end,actual_time_s=value(psspy.dsrval('TIME',0),'TIME')))
        check(psspy.dist_clear_fault(1),'dist_clear_fault')
        run_exact(c['simulation']['duration_s'])
        write_json(folder/'events.json',events)
    finally:
        psspy.pssehalt_2()
    import dyntools
    title,labels,channels=dyntools.CHNF(str(output)).get_data()
    write_json(folder/'channel_map.json',dict(title=title,labels=labels,indices=indices,model_parameters=model_parameters(c)))
    import numpy as np
    # Native FLOW1 channels are evaluated from the solved network. At this PCC,
    # Qinj = Qload(V) + Qflow(PCC->grid); the resistive fault consumes no Q.
    # Keep the model's lagged Q VAR as a separate auditable native quantity.
    v=np.asarray(channels[1]);q=np.asarray(channels[9])+op['load_q_mvar']*(v/op['pcc_voltage_pu'])**2
    # Preserve duplicate-time pre/post-event samples for exact jump integration.
    save_csv(folder/'native_channels.csv',dict(time_s=channels['time'],v_pu=v,
        i_ka=abs(np.asarray(channels[2]))*rating/(np.sqrt(3)*op['voltage_kv_ll']),q_mvar=q))
    data=normalize_channels(channels['time'],v,channels[2],q,rating,op['voltage_kv_ll'],
        native_model_q_mvar=channels[3],pcc_to_grid_p_mw=channels[8],pcc_to_grid_q_mvar=channels[9],
        integrator_state_pu=channels[7],vmeas_pu=channels[4],command_iq_pu=channels[5],vref_pu=channels[6])
    save_csv(folder/'channels.csv',data)
    checks=validate_rms(data,c,op,events,init);write_json(folder/'checks.json',checks)
    notes=[
        'Native SVSMO3T2: Kp=1/droop, Ki=0, Xc0=0. Before RUN only, move Iq0 into Vref=Vop+droop*Iq0 and zero the inactive integral state/derivative/memory. This preserves the initial command and avoids the native limiter resetting the bias.',
        '10 ms scalar voltage filter; 20 ms output lag; +/-1 pu current limit on the same rating/base.',
        'GENCLS H=0 holds internal source voltage and frequency; source plus branch impedance matches the extracted Z1.',
        'Local passive load converted to constant admittance, equal to the EMT parallel RLC at nominal frequency.',
        'Same PCC fault, resistance in ohms and requested application/clearing times; actual event times recorded.',
        'MSS, slow reset, deadband and nonlinear droop disabled; protection thresholds lie outside this run range.',
        'RMS scalar voltage and instantaneous phasor orientation differ from EMT filtered dq voltage and angle hold.',
        'RMS Q is derived from simultaneous native network FLOW1 Q plus the constant-admittance load Q; the model Q VAR can lag voltage at events and is retained separately in the CSV/OUTX.',
        'Native duplicate-time event samples are retained in native_channels.csv for discontinuous cycle integration. Final partial steps align fault boundaries within 0.2 microseconds; the nominal step is then restored.',
        'RMS algebraic network has no subcycle inductive/capacitive energy transient; EMT retains RLC energy.',
        'RMS is initialized at the operating point; EMT energization/enable at startup is excluded from comparisons.',
        'Neither model includes switching, DC energy, detailed PLL or equipment protection; equivalence is bounded to terminal controls.'
    ]
    metadata=dict(source_engine='PSS/E',model='SVSMO3T2',version=list(version),equivalent_to_emt=True,
        equivalence_scope='matched averaged terminal controller and fundamental-frequency network; documented differences remain',
        quantity_location='STATCOM injection at PCC',q_sign='positive injection',frequency_hz=op['frequency_hz'],
        voltage_kv_ll=op['voltage_kv_ll'],fault=c['fault'],time_step_s=dt,
        csv_sha256=sha256(folder/'channels.csv'),operating_point_sha256=sha256(op_path),
        model_equivalence_notes=notes,physical_checks_passed=all(x['passed'] for x in checks),
        artifacts={p.name:sha256(p) for p in folder.iterdir() if p.is_file() and p.name!='metadata.json'})
    write_json(folder/'metadata.json',metadata)
    if not metadata['physical_checks_passed']: raise RuntimeError('Native RMS physical checks failed; inspect rms/checks.json.')
    print('Native PSS/E SVSMO3T2 fault run and physical checks passed.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('operating_point');p.add_argument('folder');a=p.parse_args()
    folder=Path(a.folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    run(load_config(a.config),Path(a.operating_point).resolve(),folder)
