"""Technical figures, comparison tables and a self-contained short HTML report."""
import base64
import csv
import html
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .config import write_json, sha256
from .results import read_pscad_out, process_waveforms, save_csv, validate_emt, cycle_mean


def verify_run_inputs(run_dir):
    """Refuse stale/swapped artifacts before generating any engineering figures."""
    root=Path(run_dir)
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf8'))
    if any(manifest.get('stages',{}).get(k)!='completed' for k in ['psse','pscad']):
        raise ValueError('Both simulator stages must have completed in this run manifest.')
    def verify(relative,expected):
        path=(root/relative).resolve()
        if not path.is_relative_to(root.resolve()) or not expected or sha256(path)!=expected:
            raise ValueError(f'Artifact hash mismatch or unsafe path: {relative}')
    verify('config.json',manifest.get('config_sha256'))
    for name in ['psse/operating_point.json','pscad/provenance.json']:
        verify(name,manifest.get('file_hashes',{}).get(name))
    op=json.loads((root/'psse'/'operating_point.json').read_text(encoding='utf8'))
    verify('psse/solved.sav',op['provenance']['solved_sav_sha256'])
    provenance=json.loads((root/'pscad'/'provenance.json').read_text(encoding='utf8'))
    if provenance.get('engine')!='PSCAD/EMTDC': raise ValueError('Missing native EMT engine provenance.')
    verify('psse/operating_point.json',provenance['operating_point_sha256'])
    verify('pscad/StatcomEMT.pscx',provenance['project_sha256'])
    names=provenance.get('raw_files',{})
    if not names: raise ValueError('No native raw output hashes recorded.')
    actual={p.name for p in (root/'pscad'/'raw').iterdir() if p.is_file()}
    if actual!=set(names): raise ValueError('Native output inventory differs from provenance.')
    for name,digest in names.items(): verify('pscad/raw/'+name,digest)
    config=json.loads((root/'config.json').read_text(encoding='utf8'))
    if config.get('rms',{}).get('enabled'):
        if manifest.get('stages',{}).get('rms')!='completed':
            raise ValueError('Native RMS stage did not complete.')
        verify('rms/metadata.json',manifest.get('file_hashes',{}).get('rms/metadata.json'))
        meta=json.loads((root/'rms'/'metadata.json').read_text(encoding='utf8'))
        if meta.get('source_engine')!='PSS/E' or meta.get('physical_checks_passed') is not True:
            raise ValueError('Native RMS physical checks/provenance not valid.')
        verify('psse/operating_point.json',meta.get('operating_point_sha256'))
        required={'dynamics.outx','statcom.dyr','dynamic_powerflow.sav','channels.csv','checks.json','events.json'}
        if not required.issubset(meta.get('artifacts',{})):
            raise ValueError('Missing required native RMS artifacts.')
        actual={p.name for p in (root/'rms').iterdir() if p.is_file()}
        if actual!=set(meta['artifacts'])|{'metadata.json'}:
            raise ValueError('Native RMS artifact inventory differs from provenance.')
        for name,digest in meta['artifacts'].items(): verify('rms/'+name,digest)


def load_rms_comparison(c,op):
    settings=c['comparison']
    if not settings['rms_csv']:
        return None,'Unavailable: no equivalent PSS/E dynamic model/channel file was supplied.'
    if not settings['rms_metadata']:
        raise ValueError('A dynamic RMS CSV requires its equivalence/provenance metadata JSON.')
    path=Path(settings['rms_csv']);meta=json.loads(Path(settings['rms_metadata']).read_text(encoding='utf8'))
    if meta.get('source_engine')!='PSS/E' or meta.get('equivalent_to_emt') is not True:
        raise ValueError('Dynamic comparison requires explicit PSS/E provenance and model equivalence.')
    if meta.get('quantity_location')!='STATCOM injection at PCC' or meta.get('q_sign')!='positive injection':
        raise ValueError('RMS current and Q must be STATCOM injection at the PCC.')
    if meta.get('csv_sha256')!=sha256(path): raise ValueError('RMS CSV does not match its metadata hash.')
    for key in ['start_s','duration_s','resistance_ohm']:
        if not np.isclose(meta['fault'][key],c['fault'][key]):
            raise ValueError(f'RMS/EMT fault mismatch: {key}')
    for key in ['frequency_hz','voltage_kv_ll']:
        if not np.isclose(meta[key],op[key]): raise ValueError(f'RMS/EMT base mismatch: {key}')
    if meta.get('operating_point_sha256')!=c.get('_operating_point_sha256'):
        raise ValueError('RMS comparison must identify the same operating-point handover.')
    if not meta.get('model_equivalence_notes'):
        raise ValueError('Document load, controller, current limit and network equivalence.')
    a=np.genfromtxt(path,delimiter=',',names=True)
    for name in ['time_s','v_pu','i_ka','q_mvar']:
        if name not in a.dtype.names or not np.isfinite(a[name]).all():
            raise ValueError(f'Missing/nonfinite RMS column {name}')
    if len(a)<3 or np.any(np.diff(a['time_s'])<=0): raise ValueError('Invalid RMS time axis.')
    cycle=1/op['frequency_hz'];start=c['fault']['start_s'];end=start+c['fault']['duration_s']
    windows=[c['simulation']['prefault_window_s'],(start+2*cycle,end-2*cycle),
             (end+2*cycle,c['simulation']['duration_s'])]
    for label,(lo,hi) in zip(['pre-fault','fault interior','post-fault'],windows):
        if np.count_nonzero((a['time_s']>=lo)&(a['time_s']<=hi))<3:
            raise ValueError(f'RMS output lacks comparable {label} coverage.')
    return a,('Native PSS/E '+meta['model']+'; matched terminal controls with documented model differences.'
              if meta.get('model') else 'Supplied PSS/E dynamic channels; equivalence asserted in the input metadata.')


def table_html(rows):
    if not rows: return '<p>No comparison data available.</p>'
    keys=list(rows[0])
    return '<table><thead><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in keys)+'</tr></thead><tbody>'+''.join(
        '<tr>'+''.join('<td>'+html.escape(str(row[k]))+'</td>' for k in keys)+'</tr>' for row in rows)+'</tbody></table>'


def report(run_dir,c):
    run_dir=Path(run_dir)
    verify_run_inputs(run_dir)
    if c!=json.loads((run_dir/'config.json').read_text(encoding='utf8')):
        raise ValueError('Report configuration differs from the frozen run configuration.')
    out=run_dir/'report';out.mkdir(exist_ok=True)
    op_path=run_dir/'psse'/'operating_point.json'
    op=json.loads(op_path.read_text(encoding='utf8'))
    c=dict(c);c['_operating_point_sha256']=sha256(op_path)
    rms_meta=None
    rms_checks=[]
    if c.get('rms',{}).get('enabled'):
        c['comparison']=dict(c['comparison'],rms_csv=str(run_dir/'rms'/'channels.csv'),rms_metadata=str(run_dir/'rms'/'metadata.json'))
        rms_meta=json.loads((run_dir/'rms'/'metadata.json').read_text(encoding='utf8'))
        from .dynamic import validate_rms
        native=np.genfromtxt(run_dir/'rms'/'channels.csv',delimiter=',',names=True)
        rms_checks=validate_rms(native,c,op,
            json.loads((run_dir/'rms'/'events.json').read_text(encoding='utf8')),
            json.loads((run_dir/'rms'/'initialization.json').read_text(encoding='utf8')))
        write_json(out/'rms_checks.json',rms_checks)
    raw=run_dir/'pscad'/'raw'
    infs=list(raw.glob('*.inf'))
    if len(infs)!=1: raise ValueError(f'Expected exactly one INF file, found {len(infs)}.')
    t,ch=read_pscad_out(infs[0],basename='emt')
    required=[f'{prefix}{phase}_{unit}' for prefix,unit in [('V','kV'),('Is','kA'),('Ig','kA'),('If','kA')] for phase in 'abc']+['FaultOn','Iq_pu']
    missing=set(required)-set(ch)
    if missing: raise ValueError(f'Missing EMT channels: {sorted(missing)}')
    v=np.column_stack([ch[f'V{x}_kV'] for x in 'abc'])
    ist=np.column_stack([ch[f'Is{x}_kA'] for x in 'abc'])
    igrid=np.column_stack([ch[f'Ig{x}_kA'] for x in 'abc'])
    data=process_waveforms(t,v,ist,op['frequency_hz'],op['voltage_kv_ll'])
    grid=process_waveforms(t,v,igrid,op['frequency_hz'],op['voltage_kv_ll'])
    save_csv(out/'emt_processed.csv',{**data,'grid_i_ka':grid['i_ka'],'grid_p_mw':grid['p_mw'],'grid_q_mvar':grid['q_mvar']})
    checks=validate_emt(t,ch,c,op,data)
    write_json(out/'checks.json',checks)
    lo,hi=c['simulation']['prefault_window_s'];m=(t>=lo)&(t<=hi)
    comparisons=[]
    for name,unit,ref,measured in [
        ('PCC voltage','pu',op['pcc_voltage_pu'],data['v_pu']),
        ('STATCOM current','kA RMS',abs(op['statcom_q_mvar'])/(np.sqrt(3)*op['voltage_kv_ll']*op['pcc_voltage_pu']),data['i_ka']),
        ('STATCOM reactive power','MVAr',op['statcom_q_mvar'],data['q_mvar']),
        ('Grid current at PCC','kA RMS',op['grid_current_ka'],grid['i_ka'])]:
        observed=float(np.mean(measured[m]))
        comparisons.append({'Quantity':name,'Unit':unit,'PSS/E power flow':round(ref,7),
            'EMT pre-fault mean':float(f'{observed:.9g}'),'Absolute difference':float(f'{abs(observed-ref):.6g}')})
    with (out/'comparison.csv').open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(comparisons[0]));writer.writeheader();writer.writerows(comparisons)
    rms,rms_status=load_rms_comparison(c,op)
    dyn=[]
    if rms is not None:
        tt=rms['time_s'];cycle=1/op['frequency_hz'];start=c['fault']['start_s'];end=start+c['fault']['duration_s']
        windows=[('Full interval including events',lo,min(t[-1],tt[-1])),('Pre-fault',lo,hi),
                 ('Fault interior',start+2*cycle,end-2*cycle),('Post-fault excluding first two cycles',end+2*cycle,min(t[-1],tt[-1]))]
        from .dynamic import rms_cycle_envelopes
        native_path=run_dir/'rms'/'native_channels.csv'
        native_for_integral=np.genfromtxt(native_path,delimiter=',',names=True) if rms_meta and native_path.is_file() else rms
        aligned=rms_cycle_envelopes(native_for_integral,tt,op['frequency_hz'])
        for label,key,unit in [('Voltage','v_pu','pu'),('Current','i_ka','kA RMS'),('Reactive power','q_mvar','MVAr')]:
            filtered=aligned[key]
            for measurement,reference in [('Native phasor',rms[key]),('One-cycle phasor envelope',filtered)]:
                for window,a,b in windows:
                    valid=(tt>=a)&(tt<=b)&np.isfinite(reference)
                    if valid.sum()<3: raise ValueError('Insufficient overlapping comparable RMS/EMT time samples.')
                    emt=np.interp(tt[valid],t,data[key]);ref=reference[valid];delta=emt-ref
                    dyn.append({'Quantity':label,'Unit':unit,'RMS measurement':measurement,'Window':window,
                        'Start (s)':a,'End (s)':b,'RMS mean':float(np.mean(ref)),'EMT mean':float(np.mean(emt)),
                        'RMSE':float(np.sqrt(np.mean(delta**2))),'Maximum absolute difference':float(np.max(abs(delta))),
                        'Samples':int(valid.sum())})
        save_csv(out/'rms_cycle_envelopes.csv',aligned)
        write_json(out/'dynamic_comparison.json',dyn)
        with (out/'dynamic_comparison.csv').open('w',newline='',encoding='utf8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(dyn[0]));writer.writeheader();writer.writerows(dyn)

    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140})
    fig,axs=plt.subplots(3,1,figsize=(10,9),sharex=True,layout='constrained')
    for ax,key,label,ref in zip(axs,['v_pu','i_ka','q_mvar'],['PCC voltage (pu)','STATCOM current (kA RMS)','STATCOM Q injection (MVAr)'],
                              [op['pcc_voltage_pu'],comparisons[1]['PSS/E power flow'],op['statcom_q_mvar']]):
        ax.plot(t,data[key],label='PSCAD EMT: trailing one-cycle measurement',color='#007a8f',lw=1.4)
        ax.hlines(ref,lo,hi,label='PSS/E solved power-flow value',color='#d06b24',linestyle='--',lw=2.5)
        if rms is not None: ax.plot(native_for_integral['time_s'],native_for_integral[key],label='PSS/E native dynamic phasor',color='#9c3687',lw=1)
        ax.axvspan(c['fault']['start_s'],c['fault']['start_s']+c['fault']['duration_s'],color='#cf3345',alpha=.12,label=f"{c['fault']['duration_s']*1000:g} ms three-phase fault")
        ax.set_ylabel(label);ax.grid(alpha=.2)
    axs[0].legend(fontsize=8,loc='lower left');axs[-1].set_xlabel('Time (s)')
    if rms is not None: axs[-1].set_xlim(lo,c['simulation']['duration_s'])
    fig.suptitle(f"{op['voltage_kv_ll']:g} kV weak grid — averaged ±{c['statcom']['rating_mvar']:g} MVAr STATCOM\nSequential PSS/E → PSCAD demonstration",fontsize=14)
    fig.savefig(out/'overview.png');fig.savefig(out/'overview.svg');plt.close(fig)
    if rms is not None:
        fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True,layout='constrained')
        for ax,key,label in zip(axs,['v_pu','i_ka','q_mvar'],['PCC voltage (pu)','STATCOM current (kA RMS)','STATCOM Q injection (MVAr)']):
            ax.plot(t,data[key],label='PSCAD: one-cycle waveform measurement',color='#007a8f',lw=1.4)
            ax.plot(aligned['time_s'],aligned[key],label='PSS/E: one-cycle phasor envelope',color='#9c3687',lw=1.2)
            ax.axvspan(c['fault']['start_s'],c['fault']['start_s']+c['fault']['duration_s'],color='#cf3345',alpha=.12)
            ax.set_ylabel(label);ax.grid(alpha=.2)
        axs[0].legend(fontsize=8,loc='lower left');axs[-1].set_xlabel('Time (s)')
        axs[-1].set_xlim(c['fault']['start_s']-.04,min(c['simulation']['duration_s'],c['fault']['start_s']+c['fault']['duration_s']+.2))
        fig.suptitle('Cycle-window comparison around the fault\nMeasurement alignment does not remove model differences',fontsize=13)
        fig.savefig(out/'aligned_overview.png');fig.savefig(out/'aligned_overview.svg');plt.close(fig)
    fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True,layout='constrained')
    colors=['#007a8f','#d06b24','#7c4b9c']
    for ax,values,label in zip(axs,[v,ist,igrid],['PCC phase voltage (kV)','STATCOM injected current (kA)','Grid current into PCC (kA)']):
        for k,col in enumerate(colors): ax.plot(t,values[:,k],color=col,lw=.8,label='Phase '+'ABC'[k])
        ax.set_ylabel(label);ax.grid(alpha=.2)
        ax.axvspan(c['fault']['start_s'],c['fault']['start_s']+c['fault']['duration_s'],color='#cf3345',alpha=.12)
    axs[0].legend(ncol=3,loc='upper right');axs[-1].set_xlim(c['fault']['start_s']-.05,c['fault']['start_s']+c['fault']['duration_s']+.08)
    axs[-1].set_xlabel('Time (s)');fig.suptitle('Native EMT instantaneous waveforms around the fault')
    fig.savefig(out/'waveforms.png');fig.savefig(out/'waveforms.svg');plt.close(fig)
    def image(name):
        encoded=base64.b64encode((out/name).read_bytes()).decode('ascii')
        return f'<img alt="{name}" src="data:image/png;base64,{encoded}">'
    passed=all(x['passed'] for x in [*checks,*rms_checks])
    metrics={'validation_passed':passed,'prefault_voltage_pu':float(np.mean(data['v_pu'][m])),
        'prefault_q_mvar':float(np.mean(data['q_mvar'][m])),
        'minimum_cycle_voltage_pu':float(np.nanmin(data['v_pu'][t>=lo])),
        'maximum_cycle_voltage_pu':float(np.nanmax(data['v_pu'][t>=lo])),
        'maximum_cycle_q_mvar':float(np.nanmax(data['q_mvar'][t>=lo])),
        'maximum_absolute_cycle_active_power_mw':float(np.nanmax(abs(data['p_mw'][t>=lo]))),
        'maximum_cycle_statcom_current_ka':float(np.nanmax(data['i_ka'])),
        'dynamic_rms_comparison_available':rms is not None}
    write_json(out/'metrics.json',metrics)
    parameter_rows=[{'Parameter':label,'Value':f'{op[key]:.8g}','Unit':unit} for label,key,unit in [
        ('External-grid resistance','r_ohm','ohm/phase'),('External-grid inductance','l_h','H/phase'),
        ('Internal source voltage','source_kv_ll','kV line-line RMS'),('Internal source phase','source_phase_deg','degrees'),
        ('Nominal short-circuit level','short_circuit_mva_nominal','MVA'),('SCR on STATCOM rating','scr',''),
        ('Rated STATCOM current','rated_current_ka','kA RMS')]]
    check_rows=[{'Check':x['check'],'Status':'PASS' if x['passed'] else 'FAIL','Actual':f"{x['actual']:.7g}",'Limit/target':f"{x['limit']:.7g}"} for x in checks]
    rms_details=''
    if rms_meta:
        rms_details='<h3>Native RMS checks</h3>'+table_html([{'Check':x['name'],'Status':'PASS' if x['passed'] else 'FAIL','Evidence':x['detail']} for x in rms_checks])
        rms_details+='<h3>Model mapping and remaining differences</h3><ul>'+''.join('<li>'+html.escape(note)+'</li>' for note in rms_meta['model_equivalence_notes'])+'</ul>'
    dynamic_text=('Differences below are descriptive, not pass/fail model accuracy limits. The full interval includes fault inception and clearing. '
                  'Windowed metrics separately show settled behavior. One-cycle phasor envelopes use RMS-of-envelope V/I and mean Q; '
                  'they reduce measurement-window mismatch but cannot reconstruct EMT subcycle oscillations. '
                  'Unfiltered phasors remain in the overview and native CSV.' if rms is not None else
                  'A matched DYR/control model, any required model DLLs, channel output and equivalence metadata are needed. The input templates describe these requirements.')
    if rms_meta:
        dynamic_text=('Native DYR, solved dynamic SAV, diagnostic initialized snapshot, OUTX, channels, event log and hashes are included in the rms folder. '
                      'The initial current bias is moved into the voltage reference once before RUN; the inactive integral state remains zero. '+dynamic_text)
    dynamic_rows=[{'Quantity':f"{r['Quantity']} ({r['Unit']})",'RMS measurement':r['RMS measurement'],
        'Window':r['Window'],'RMSE':f"{r['RMSE']:.6g}",'Max. difference':f"{r['Maximum absolute difference']:.6g}",
        'Samples':r['Samples']} for r in dyn]
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sequential RMS–EMT technical report</title><style>body{{font:16px/1.5 system-ui,sans-serif;max-width:1050px;margin:40px auto;padding:0 24px;color:#172b40}}h1{{line-height:1.15}}h2{{margin-top:34px}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:8px;border-bottom:1px solid #d5dce2;text-align:left}}th{{background:#edf3f6}}img{{width:100%;height:auto}}.status{{padding:14px;background:#edf3f6;border-left:5px solid #007a8f}}code{{background:#edf3f6;padding:2px 5px}}@media print{{body{{margin:0;font-size:11px}}h2{{break-after:avoid}}img,table{{break-inside:avoid}}}}</style>
<h1>Sequential RMS–EMT integration</h1><p>{op['voltage_kv_ll']:g} kV weak grid · ±{c['statcom']['rating_mvar']:g} MVAr averaged STATCOM · {c['fault']['duration_s']*1000:g} ms three-phase fault</p>
<p class="status">Engineering checks: <strong>{'PASS' if passed else 'FAIL — results require investigation'}</strong>. Real PSS/E power-flow/ASCC and PSCAD/EMTDC outputs were used. Dynamic RMS comparison: {html.escape(rms_status)}</p>
<h2>Method and scope</h2><p>PSS/E solves the operating point and extracts the external-grid positive-sequence Thévenin impedance. Python reconstructs the source behind this impedance, converts bases and transfers parameters into a newly generated PSCAD case. PSCAD then runs independently. This is sequential, offline integration, without shared time stepping, real-time synchronization or feedback to PSS/E.</p>
<p>The STATCOM is an averaged reactive current injection model. Its voltage droop is {c['statcom']['droop_pu']:.3g} pu, current response time constant {c['statcom']['current_tau_s']:.3g} s, and maximum phase RMS current {op['rated_current_ka']:.6g} kA. ±{c['statcom']['rating_mvar']:g} MVAr is the nominal-voltage capability; Q falls with voltage at the current limit. A 10 ms rotating-frame voltage filter and an ideal fixed-frequency reference are used. The model excludes PWM, DC-link energy, PLL synchronization dynamics, transformer/converter losses, protection and manufacturer controls. Filtered-angle tracking permits transient active-power exchange without a DC-energy constraint. It is a terminal surrogate and cannot establish hardware performance.</p>
<p>The local load is converted to parallel R, L and C branches matching its solved pre-fault net P/Q. A configurable {op['pcc_capacitance_f']*1e9:g} nF per-phase PCC capacitance represents an assumed aggregate terminal capacitance; it is not inferred from PSS/E or measured equipment. The parallel inductor is adjusted to preserve net Q. This finite capacitance regularizes the fast clearing transient. This is a constant-impedance EMT load; its fault response is not a constant-power load response. The fault is three simultaneous phase-to-ground resistances of {c['fault']['resistance_ohm']:.6g} Ω, applied from {c['fault']['start_s']:.6g} to {c['fault']['start_s']+c['fault']['duration_s']:.6g} s and cleared without line tripping.</p>
<h2>Transferred electrical parameters</h2>{table_html(parameter_rows)}
<p>Three-phase bases: Zbase = VLL²/Sbase and Ibase = Sbase/(√3 VLL). Boundary power is positive into the retained PCC. I = conjugate(S/V); E = V + ZI. All phasors use the phase-A RMS convention. Positive STATCOM Q means injection into the grid. ASCC uses 1 pu voltage with loads, shunts, charging and FACTS excluded; its short-circuit current is a grid-strength check, not the fault trace with STATCOM connected.</p>
<h2>Measurements and comparison</h2><p>EMT voltage and current are trailing one-cycle total RMS values; P is the cycle mean of Σvi and Q is the cycle mean of the balanced Clarke-frame reactive-power expression. These are appropriate for this balanced averaged model. They do not constitute a general fundamental-sequence estimator for distorted switching waveforms. The first incomplete cycle is omitted. PSS/E power flow is compared only over {lo}–{hi} s; startup and fault transients are excluded.</p>
{table_html(comparisons)}{image('overview.png')}{image('waveforms.png')}
<h2>Physical consistency checks</h2>{table_html(check_rows)}
<p>Over the analyzed interval, maximum one-cycle voltage was {metrics['maximum_cycle_voltage_pu']:.4f} pu and maximum Q was {metrics['maximum_cycle_q_mvar']:.3f} MVAr. Maximum absolute cycle-averaged terminal active power was {metrics['maximum_absolute_cycle_active_power_mw']:.3f} MW. Clearing transients and overvoltage depend strongly on this simplified controller and the constant-impedance load. Passing the listed numerical/network checks does not qualify equipment limits or the missing DC-energy and protection behavior.</p>
<h2>Dynamic RMS comparison</h2><p>{html.escape(rms_status)} No dynamic PSS/E trace is synthesized from the EMT signal or power flow. {dynamic_text}</p>{rms_details}{image('aligned_overview.png') if rms is not None else ''}{table_html(dynamic_rows)}
<h2>Reproducibility</h2><p>This run retains the input configuration, solved SAV, operating-point JSON, generated PSCX, native INF/OUT files, simulator logs and SHA-256 provenance. See <code>manifest.json</code>, <code>psse/operating_point.json</code> and <code>pscad/provenance.json</code>. Re-run the documented CLI in Python 3.11 with licensed PSS/E 35.6 and PSCAD 5.1.0 and the configured compiler.</p>
<p>API references: <a href="https://www.pscad.com/webhelp-v502-al/reference/launching.html">PSCAD launch</a>, <a href="https://www.pscad.com/webhelp-v502-al/reference/project.html">project build/run</a>, <a href="https://www.pscad.com/webhelp-v502-al/reference/wizard.html">Component Wizard</a>. PSS/E APIs were checked against the installed 35.6 API manual and Python docstrings; see the project's API reference document.</p></html>'''
    (out/'report.html').write_text(page,encoding='utf8')
    return metrics
